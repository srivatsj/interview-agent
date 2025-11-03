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
    app_name: str = "test_interview_agent",
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
    app_name: str = "test_interview_agent",
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
    app_name: str = "test_interview_agent",
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
