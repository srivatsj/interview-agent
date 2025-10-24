"""
Intro Agent for System Design Interview

Collects candidate background and explains interview format.
"""

from google.adk.agents import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools import ToolContext

from ..constants import MODEL_NAME
from ..prompts.prompt_loader import load_prompt
from ..schemas import CandidateInfo


def save_candidate_info(
    name: str, years_experience: int, domain: str, projects: str, tool_context: ToolContext
) -> str:
    """Save candidate background information to session state.

    Use this after collecting the candidate's background information.

    Args:
        name: Candidate's full name
        years_experience: Years of professional experience
        domain: Primary domain expertise
        projects: Notable projects they've worked on
        tool_context: Tool execution context

    Returns:
        Confirmation message
    """
    candidate_info = CandidateInfo(
        name=name, years_experience=years_experience, domain=domain, projects=projects
    )

    # Use tool_context.state (recommended by ADK docs)
    tool_context.state["candidate_info"] = candidate_info.model_dump()

    return f"Candidate info saved: {name}, {years_experience} years experience"


def get_intro_instruction(ctx: ReadonlyContext) -> str:
    """Generate instruction with routing_decision from session state."""
    routing_decision = ctx.session.state.get("routing_decision", {})
    company = routing_decision.get("company", "COMPANY")
    interview_type = routing_decision.get("interview_type", "INTERVIEW_TYPE")

    # Load the template and substitute the values (template uses {{ }} mustache syntax)
    template = load_prompt("intro_agent.txt")
    return template.replace("{{routing_decision.company}}", company).replace(
        "{{routing_decision.interview_type}}", interview_type
    )


intro_agent = Agent(
    model=MODEL_NAME,
    name="intro_agent",
    description="Greets candidate, collects background information, and explains interview format",
    tools=[save_candidate_info],
    instruction=get_intro_instruction,
)
