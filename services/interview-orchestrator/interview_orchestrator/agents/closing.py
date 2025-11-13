"""Closing agent for wrapping up the interview."""

from google.adk.agents import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools import ToolContext

from ..shared.constants import get_gemini_model
from ..shared.prompts.prompt_loader import load_prompt


def mark_interview_complete(tool_context: ToolContext) -> str:
    """Mark the entire interview as complete and end the session.

    Returns:
        Confirmation message
    """
    tool_context.state["interview_complete"] = True
    tool_context.state["interview_phase"] = "done"

    return "Interview marked as complete. Thank you for using the interview system!"


def get_closing_instruction(ctx: ReadonlyContext) -> str:
    """Get closing instruction with interview context."""
    routing = ctx.session.state.get("routing_decision", {})
    candidate_info = ctx.session.state.get("candidate_info", {})

    return load_prompt(
        "closing_agent.txt",
        company=routing.get("company", "COMPANY"),
        interview_type=routing.get("interview_type", "INTERVIEW_TYPE"),
        candidate_name=candidate_info.get("name", "candidate"),
    )


closing_agent = Agent(
    name="closing_agent",
    model=get_gemini_model(),
    description="Wraps up the interview session",
    instruction=get_closing_instruction,
    tools=[mark_interview_complete],
)
