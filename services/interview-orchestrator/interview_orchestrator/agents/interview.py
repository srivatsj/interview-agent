"""Interview agent wrapper that routes to design or coding based on interview type."""

from google.adk.agents import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.genai import types

from ..shared.constants import get_gemini_model
from .interview_types.coding import coding_interview_agent
from .interview_types.design import design_interview_agent


def _get_interview_instruction(ctx: ReadonlyContext) -> str:
    """Route to appropriate interview agent based on type."""
    routing = ctx.session.state.get("routing_decision", {})
    interview_type = routing.get("interview_type", "system_design")

    if interview_type == "coding":
        return """You are a ROUTER. You are NOT conversational.
DO NOT generate a conversational response.
DO NOT talk to the user. DO NOT ask questions. DO NOT conduct the interview.

Your ONLY job: Transfer to coding_interview_agent immediately WITHOUT saying anything to the user.

The coding_interview_agent will conduct the interview."""
    else:  # system_design
        return """You are a ROUTER. You are NOT conversational.
DO NOT generate a conversational response.
DO NOT talk to the user. DO NOT ask questions. DO NOT conduct the interview.

Your ONLY job: Transfer to design_interview_agent immediately WITHOUT saying anything to the user.

The design_interview_agent will conduct the interview."""


# Main interview agent that routes to specific interview types
interview_agent = Agent(
    name="interview_agent",
    model=get_gemini_model(),
    description="Routes to appropriate interview type (design or coding)",
    instruction=_get_interview_instruction,
    sub_agents=[design_interview_agent, coding_interview_agent],
    tools=[],
    generate_content_config=types.GenerateContentConfig(
        temperature=0.0,  # Maximum determinism - just transfer, no conversation
    ),
)
