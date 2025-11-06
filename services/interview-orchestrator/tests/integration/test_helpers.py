"""
Test Helpers for Integration Tests

Provides helper functions to set up session state without LLM calls.
This enables test independence while minimizing API costs.

Usage:
    session = await create_session_with_routing(
        session_service,
        company="google",
        interview_type="system_design"
    )
"""

import time

from google.adk.events import Event, EventActions
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part


async def create_fresh_session(
    session_service: InMemorySessionService,
    app_name: str = "test_interview_orchestrator",
    user_id: str = "test_user",
):
    """
    Create a fresh session with no state.

    Args:
        session_service: Session service to use
        app_name: Application name
        user_id: User ID

    Returns:
        Fresh session object
    """
    return await session_service.create_session(
        user_id=user_id,
        app_name=app_name,
    )


async def create_session_with_routing(
    session_service: InMemorySessionService,
    company: str,
    interview_type: str,
    app_name: str = "test_interview_orchestrator",
    user_id: str = "test_user",
):
    """
    Create a session with routing decision already set.

    This bypasses the routing LLM calls for tests that need to start
    at a later phase (e.g., intro, design questions).

    Uses the official append_event() method to update state properly.

    Args:
        session_service: Session service to use
        company: Company name (e.g., "google", "meta", "amazon")
        interview_type: Interview type (e.g., "system_design", "coding")
        app_name: Application name
        user_id: User ID

    Returns:
        Session with routing_decision in state
    """
    session = await session_service.create_session(
        user_id=user_id,
        app_name=app_name,
    )

    # Use official append_event() method to set state
    # This matches what set_routing_decision tool creates
    state_delta = {
        "routing_decision": {
            "company": company.lower(),
            "interview_type": interview_type.lower(),
            "confidence": 1.0,
        }
    }

    event = Event(
        author="test_helper",
        actions=EventActions(state_delta=state_delta),
        timestamp=time.time(),
    )

    await session_service.append_event(session, event)

    return session


async def create_session_with_candidate_info(
    session_service: InMemorySessionService,
    company: str,
    interview_type: str,
    name: str,
    years_experience: int,
    domain: str,
    app_name: str = "test_interview_orchestrator",
    user_id: str = "test_user",
):
    """
    Create a session with routing and candidate info already set.

    This bypasses routing and intro phases for tests that need to start
    at design phase.

    Uses the official append_event() method to update state properly.

    Args:
        session_service: Session service to use
        company: Company name
        interview_type: Interview type
        name: Candidate name
        years_experience: Years of experience
        domain: Domain expertise
        app_name: Application name
        user_id: User ID

    Returns:
        Session with routing_decision and candidate_info in state
    """
    session = await session_service.create_session(
        user_id=user_id,
        app_name=app_name,
    )

    # Use official append_event() method to set all state at once
    state_delta = {
        "routing_decision": {
            "company": company.lower(),
            "interview_type": interview_type.lower(),
            "confidence": 1.0,
        },
        "candidate_info": {
            "name": name,
            "years_experience": years_experience,
            "domain": domain,
        },
        "interview_phase": "design",
    }

    event = Event(
        author="test_helper",
        actions=EventActions(state_delta=state_delta),
        timestamp=time.time(),
    )

    await session_service.append_event(session, event)

    return session


def create_user_message(text: str) -> Content:
    """Create a user message for ADK runner.

    Args:
        text: Message text content

    Returns:
        Content object with user role and text part
    """
    return Content(role="user", parts=[Part(text=text)])


async def send_message(runner: Runner, session, message: str):
    """Send a message and consume all events.

    Args:
        runner: ADK Runner instance
        session: Session object with user_id and session_id
        message: Message text to send

    Returns:
        None (events are consumed)
    """
    async for _ in runner.run_async(
        user_id=session.user_id,
        session_id=session.id,
        new_message=create_user_message(message),
    ):
        pass


async def get_session_state(session_service: InMemorySessionService, session):
    """Get current session state.

    Args:
        session_service: Session service instance
        session: Session object

    Returns:
        Dictionary of current session state
    """
    updated_session = await session_service.get_session(
        app_name=session.app_name,
        user_id=session.user_id,
        session_id=session.id,
    )
    return updated_session.state


async def get_last_agent_message(session_service: InMemorySessionService, session) -> str:
    """Get the last message from the agent.

    Args:
        session_service: Session service instance
        session: Session object

    Returns:
        Last agent message text, or empty string if no messages
    """
    updated_session = await session_service.get_session(
        app_name=session.app_name,
        user_id=session.user_id,
        session_id=session.id,
    )

    # Iterate backwards through events to find last non-user message
    for event in reversed(updated_session.events):
        if event.author != "user" and event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    return part.text
    return ""


class CandidateResponseGenerator:
    """Generates realistic candidate responses using LLM for E2E tests.

    This simulates a human candidate responding to interview questions,
    enabling realistic multi-turn conversation testing without hardcoded responses.
    """

    def __init__(self, model: str = "gemini-2.0-flash-exp"):
        """Initialize the candidate response generator.

        Args:
            model: Gemini model to use for generating responses
        """
        self.model = model
        self.client = None
        self.llm_call_count = 0

    def _get_client(self):
        """Lazy initialize the Gemini client."""
        if self.client is None:
            from google import genai  # noqa: PLC0415

            self.client = genai.Client()
        return self.client

    async def generate_response(
        self,
        interviewer_message: str,
        phase: str,
        candidate_profile: dict | None = None,
    ) -> str:
        """Generate a realistic candidate response using LLM.

        Args:
            interviewer_message: The interviewer's question/prompt
            phase: Current interview phase (e.g., "routing", "intro", "problem_clarification")
            candidate_profile: Optional candidate profile (name, experience, domain)

        Returns:
            Generated candidate response text
        """
        client = self._get_client()

        # Build candidate persona
        profile = candidate_profile or {}

        # Special handling for closing phase
        if phase == "closing_question":
            persona = f"""You are a software engineering candidate being interviewed.
Your profile:
- Name: {profile.get("name", "Alex Chen")}
- Experience: {profile.get("years_experience", 5)} years

The interview technical portion has just completed. The interviewer is wrapping up.
You should ask 1-2 professional questions about:
- Next steps in the interview process
- Timeline for feedback
- The role or company

Keep it brief and professional (1-2 sentences).
"""
        elif phase == "closing_thanks":
            persona = f"""You are a software engineering candidate being interviewed.
Your profile:
- Name: {profile.get("name", "Alex Chen")}

The interviewer just answered your questions. Now thank them warmly and say goodbye.
Keep it brief and genuine (1-2 sentences).
Examples:
- "Thank you so much for your time today! I really enjoyed our conversation."
- "Thanks for the great discussion! Looking forward to hearing back."
"""
        else:
            persona = f"""You are a software engineering candidate being interviewed.
Your profile:
- Name: {profile.get("name", "Alex Chen")}
- Experience: {profile.get("years_experience", 5)} years
- Domain: {profile.get("domain", "distributed systems")}
- Notable: Worked at tech companies on scalable systems

Respond naturally and concisely to the interviewer's question.
Current phase: {phase}

IMPORTANT:
- Be direct and specific
- For routing: state your preference clearly
- For intro: share your background naturally
- For design: provide technical details with keywords
- Keep responses focused (2-4 sentences)
"""

        prompt = f"""{persona}

Interviewer: {interviewer_message}

Candidate response:"""

        response = await client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
        )

        self.llm_call_count += 1

        return response.text.strip()
