"""
Closing Agent for System Design Interview

Wraps up the interview, answers questions, and provides summary.
"""

from google.adk.agents import Agent
from google.adk.agents.readonly_context import ReadonlyContext

from ..constants import MODEL_NAME
from ..prompts.prompt_loader import load_prompt


def get_closing_instruction(ctx: ReadonlyContext) -> str:
    """Generate instruction with routing_decision and candidate_info from session state."""
    routing_decision = ctx.session.state.get("routing_decision", {})
    candidate_info = ctx.session.state.get("candidate_info", {})

    company = routing_decision.get("company", "COMPANY")
    interview_type = routing_decision.get("interview_type", "INTERVIEW_TYPE")
    candidate_name = candidate_info.get("name", "CANDIDATE")

    # Load the template and substitute the values
    # Note: template uses {{var}} which becomes {var} after load_prompt's .format() call
    template = load_prompt("closing_agent.txt")
    return (
        template.replace("{routing_decision.company}", company)
        .replace("{routing_decision.interview_type}", interview_type)
        .replace("{candidate_info.name}", candidate_name)
    )


closing_agent = Agent(
    model=MODEL_NAME,
    name="closing_agent",
    description="Wraps up the interview, answers candidate questions, and provides encouragement",
    instruction=get_closing_instruction,
)
