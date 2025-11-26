"""Intro agent for collecting candidate information."""

import logging

from google.adk.agents import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools import ToolContext

from ..shared.constants import get_gemini_model
from ..shared.prompts.prompt_loader import load_prompt
from ..shared.schemas.candidate_info import CandidateInfo

logger = logging.getLogger(__name__)


def save_candidate_info(
    name: str,
    years_experience: int,
    domain: str,
    projects: str,
    tool_context: ToolContext,
) -> str:
    """Save candidate background information and transition to interview phase.

    Args:
        name: Candidate's full name
        years_experience: Years of professional experience
        domain: Primary domain expertise (e.g., "backend systems", "mobile")
        projects: Notable projects they've worked on
        tool_context: Tool execution context

    Returns:
        Confirmation message
    """
    candidate_info = CandidateInfo(
        name=name,
        years_experience=years_experience,
        domain=domain,
        projects=projects,
    )

    tool_context.state["candidate_info"] = candidate_info.model_dump()
    tool_context.state["interview_phase"] = "interview"

    logger.info(f"Candidate info saved: {name}, transitioning to interview phase")

    return (
        f"Candidate info saved successfully. "
        f"IMPORTANT: Transfer to interview_coordinator immediately so it can route to the interview agent."
    )


def get_intro_instruction(ctx: ReadonlyContext) -> str:
    """Get intro instruction with routing context."""
    routing = ctx.session.state.get("routing_decision", {})
    return load_prompt(
        "intro_agent.txt",
        company=routing.get("company", "COMPANY"),
        interview_type=routing.get("interview_type", "INTERVIEW_TYPE"),
    )


intro_agent = Agent(
    name="intro_agent",
    model=get_gemini_model(),
    description="Collects candidate background information",
    instruction=get_intro_instruction,
    tools=[save_candidate_info],
)
