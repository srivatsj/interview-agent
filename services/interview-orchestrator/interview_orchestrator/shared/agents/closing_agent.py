"""
Closing Agent for System Design Interview

Wraps up the interview, answers questions, and provides summary.
"""

from google.adk.agents import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools import ToolContext

from ..constants import MODEL_NAME
from ..prompts.prompt_loader import load_prompt


def mark_closing_complete(tool_context: ToolContext) -> str:
    """Mark the closing phase as complete.

    Call this tool when you have:
    1. Thanked the candidate
    2. Answered all their questions (or confirmed they have none)
    3. Provided encouraging closing remarks

    Returns:
        Confirmation message
    """
    tool_context.state["closing_complete"] = True
    return "Closing phase marked as complete. Interview session will end after your final message."


def get_closing_instruction(ctx: ReadonlyContext) -> str:
    """Generate instruction with routing_decision and candidate_info from session state."""
    routing_decision = ctx.session.state.get("routing_decision", {})
    candidate_info = ctx.session.state.get("candidate_info", {})

    company = routing_decision.get("company", "COMPANY")
    interview_type = routing_decision.get("interview_type", "INTERVIEW_TYPE")
    candidate_name = candidate_info.get("name", "CANDIDATE")

    return load_prompt(
        "closing_agent.txt",
        company=company,
        interview_type=interview_type,
        candidate_name=candidate_name,
    )


def create_closing_agent() -> Agent:
    """Create a new closing agent instance.

    Returns a new agent instance to avoid parent agent conflicts.
    """
    return Agent(
        model=MODEL_NAME,
        name="closing_agent",
        description="Wraps up interview, answers questions, and provides encouragement",
        tools=[mark_closing_complete],
        instruction=get_closing_instruction,
    )


# Module-level instance for backward compatibility
closing_agent = create_closing_agent()
