"""Simple Interview POC using Sequential + Custom Agent patterns.

This demonstrates:
1. Sequential Agent for deterministic phase flow
2. Custom Agent for guaranteed remote expert calls
3. Compatible with Gemini Live API (audio streaming)
"""

import logging
from typing import AsyncGenerator

from google.adk.agents import Agent, BaseAgent, SequentialAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.tools import ToolContext
from pydantic import PrivateAttr

from ..shared.constants import get_gemini_model

logger = logging.getLogger(__name__)


# ============================================================================
# PHASE 1: INTRO - Collect candidate info
# ============================================================================

def save_candidate_info(
    name: str,
    experience_years: int,
    tool_context: ToolContext,
) -> str:
    """Save candidate information and transition to interview phase.

    CRITICAL: Call this IMMEDIATELY when you have both pieces of info.

    Args:
        name: Candidate's name
        experience_years: Years of experience
        tool_context: Tool execution context

    Returns:
        Confirmation message
    """
    tool_context.state["candidate_name"] = name
    tool_context.state["candidate_experience"] = experience_years
    tool_context.state["phase_complete"] = "intro"

    logger.info(f"✅ Candidate info saved: {name}, {experience_years} years")

    return f"Thanks {name}! I've noted you have {experience_years} years of experience."


intro_agent = Agent(
    name="intro_agent",
    model=get_gemini_model(),
    description="Collects candidate information",
    instruction="""Collect 2 pieces of information:
1. Candidate's name
2. Years of experience (as a number)

As SOON as you have BOTH pieces, call save_candidate_info tool.

DO NOT:
- Proceed to technical discussion
- Ask multiple follow-up questions
- Wait for them to say they're ready

Just collect the 2 pieces and call the tool immediately.""",
    tools=[save_candidate_info],
    output_key="intro_result"
)


# ============================================================================
# PHASE 2: INTERVIEW - Custom Agent with Forced Expert Calls
# ============================================================================

async def ask_expert(question: str, tool_context: ToolContext) -> str:
    """Get expert feedback on candidate's answer.

    Args:
        question: Candidate's answer or question
        tool_context: Tool execution context

    Returns:
        Expert feedback
    """
    # Access state directly from tool_context
    state = tool_context.state

    # Mark that expert was called
    call_count = state.get("expert_calls", 0) + 1
    state["expert_calls"] = call_count

    # Mark interview phase complete after first expert call
    if state.get("phase_complete") == "intro":
        state["phase_complete"] = "interview"

    logger.info(f"🔗 Expert call #{call_count}: {question[:100]}...")

    # Simulate expert response (in real implementation, this calls remote agent)
    candidate_name = state.get("candidate_name", "Candidate")
    return f"""Expert feedback for {candidate_name}:

Regarding '{question[:100]}...':
- Good approach to the problem
- Consider discussing scalability implications
- Ask about trade-offs in the design

Follow-up: "Can you explain how this would scale to handle 1M users?"
"""


class InterviewCustomAgent(BaseAgent):
    """Custom agent that FORCES expert consultation for every candidate response.

    This guarantees that ask_expert is called before every interviewer response,
    eliminating the unreliability of LLM-based tool selection.
    """

    def __init__(self, **kwargs):
        """Initialize interview agent with response formatter."""

        # Response formatter - presents expert feedback naturally
        response_formatter = Agent(
            name="response_formatter",
            model=get_gemini_model(),
            description="Formats expert feedback conversationally",
            instruction="""You're conducting a technical interview.

The expert has provided this feedback:
{expert_feedback}

Your job:
1. Present this feedback naturally to the candidate
2. Ask the follow-up question suggested
3. Keep it conversational and encouraging

Candidate name: {candidate_name}
"""
        )

        # Initialize BaseAgent with formatter as sub-agent
        super().__init__(
            sub_agents=[response_formatter],
            **kwargs
        )

        logger.info("✨ InterviewCustomAgent created with forced expert calls")

    async def _run_async_impl(
        self,
        ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Custom execution that FORCES expert call before every response."""

        # Extract user message from user_content
        user_message = ""
        if ctx.user_content and ctx.user_content.parts:
            user_message = " ".join([p.text for p in ctx.user_content.parts if p.text])

        response_formatter = self.sub_agents[0]  # Get the response formatter

        logger.info(f"🎯 Interview Agent: Processing '{user_message[:50]}...'")

        if not user_message:
            # No input, just run formatter
            async for event in response_formatter.run_async(ctx):
                yield event
            return

        # FORCE expert call (no LLM decision!)
        logger.info("🔨 FORCING expert call...")

        try:
            # Create tool context from invocation context
            tool_ctx = ToolContext(invocation_context=ctx)

            # Call expert directly
            expert_feedback = await ask_expert(user_message, tool_ctx)
            logger.info(f"✅ Expert returned: {expert_feedback[:100]}...")

            # Store in state for formatter
            ctx.session.state["expert_feedback"] = expert_feedback

        except Exception as e:
            logger.error(f"❌ Expert call failed: {e}")
            ctx.session.state["expert_feedback"] = f"Error getting feedback: {e}"

        # Let formatter present the feedback
        logger.info("🤖 Running response formatter")
        async for event in response_formatter.run_async(ctx):
            yield event

        logger.info("✅ Interview turn complete")


# Create interview agent instance
interview_agent = InterviewCustomAgent(
    name="interview_agent",
    description="Conducts technical interview with expert consultation"
)


# ============================================================================
# PHASE 3: CLOSING - Wrap up
# ============================================================================

closing_agent = Agent(
    name="closing_agent",
    model=get_gemini_model(),
    description="Wraps up the interview",
    instruction="""Thank the candidate for their time.

Candidate: {candidate_name}
Expert calls made: {expert_calls}

Keep it brief and professional. Mention they did well.""",
    output_key="closing_result"
)


# ============================================================================
# PHASE WRAPPERS: Conditional Execution Based on State
# ============================================================================

class ConditionalAgent(BaseAgent):
    """Wrapper agent that only runs if condition is met."""

    _condition_fn: object = PrivateAttr()

    def __init__(self, condition_fn, wrapped_agent: BaseAgent, **kwargs):
        """Initialize conditional agent.

        Args:
            condition_fn: Function taking session state, returns True if should run
            wrapped_agent: The agent to run if condition is met
        """
        super().__init__(
            name=wrapped_agent.name,
            description=wrapped_agent.description,
            sub_agents=[wrapped_agent],
            **kwargs
        )
        # Set private attribute after super().__init__
        self._condition_fn = condition_fn

    async def _run_async_impl(
        self,
        ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Run wrapped agent only if condition is met."""
        wrapped_agent = self.sub_agents[0]

        # Check condition
        if not self._condition_fn(ctx.session.state):
            logger.info(f"⏭️  Skipping {wrapped_agent.name} (condition not met)")
            return

        logger.info(f"▶️  Running {wrapped_agent.name} (condition met)")

        # Run the wrapped agent
        async for event in wrapped_agent.run_async(ctx):
            yield event


# Wrap agents with conditions
intro_conditional = ConditionalAgent(
    condition_fn=lambda state: state.get("phase_complete") != "intro",
    wrapped_agent=intro_agent
)

interview_conditional = ConditionalAgent(
    condition_fn=lambda state: state.get("phase_complete") == "intro",
    wrapped_agent=interview_agent
)

closing_conditional = ConditionalAgent(
    condition_fn=lambda state: state.get("phase_complete") == "interview",
    wrapped_agent=closing_agent
)


# ============================================================================
# ROOT: Sequential Agent for Deterministic Flow
# ============================================================================

root_agent = SequentialAgent(
    name="simple_interview",
    description="Simple interview flow: intro → interview → closing",
    sub_agents=[
        intro_conditional,    # Phase 1: Only runs if not completed
        interview_conditional,  # Phase 2: Only runs if intro completed
        closing_conditional     # Phase 3: Only runs if interview completed
    ]
)
