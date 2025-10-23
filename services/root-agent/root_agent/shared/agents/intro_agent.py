"""
Intro Agent for System Design Interview

Collects candidate background and explains interview format.
"""

from google.adk.agents import Agent
from google.adk.tools import ToolContext

from ..constants import MODEL_NAME
from ..prompts.prompt_loader import load_prompt
from ..schemas import CandidateInfo


def save_candidate_info(
    tool_context: ToolContext, name: str, years_experience: int, domain: str, projects: str
) -> str:
    """Save candidate background information to session state.

    Use this after collecting the candidate's background information.

    Args:
        name: Candidate's full name
        years_experience: Years of professional experience
        domain: Primary domain expertise
        projects: Notable projects they've worked on

    Returns:
        Confirmation message
    """
    candidate_info = CandidateInfo(
        name=name, years_experience=years_experience, domain=domain, projects=projects
    )

    tool_context.session.state["candidate_info"] = candidate_info.model_dump()

    return f"Candidate info saved: {name}, {years_experience} years experience"


intro_agent = Agent(
    model=MODEL_NAME,
    name="intro_agent",
    description="Greets candidate, collects background information, and explains interview format",
    tools=[save_candidate_info],
    instruction=load_prompt("intro_agent.txt"),
)
