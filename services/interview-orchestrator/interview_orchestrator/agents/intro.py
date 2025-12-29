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

    CRITICAL: Call this tool IMMEDIATELY when you have collected ALL 4 pieces:
    1. name - The candidate's full name
    2. years_experience - Years of professional experience (as integer)
    3. domain - Primary domain expertise (e.g., "distributed systems", "backend")
    4. projects - Notable projects they've worked on

    After collecting this information through conversation, call this tool to
    save it and automatically transition to the interview phase. Do NOT wait
    for the candidate to say they're ready. Call as soon as you have all 4 pieces.

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

    # Set default interview question based on interview type
    routing = tool_context.state.get("routing_decision", {})
    interview_type = routing.get("interview_type", "system_design")

    if interview_type == "system_design":
        tool_context.state["interview_question"] = "Design a URL shortening service (like bit.ly)"
    elif interview_type == "coding":
        tool_context.state["interview_question"] = "Implement a function to find the longest substring without repeating characters"
    else:
        tool_context.state["interview_question"] = "Technical interview question"

    logger.info(f"Candidate info saved: {name}, transitioning to interview phase")

    return (
        f"Candidate info saved: {name}, {years_experience} years experience "
        f"in {domain}. Moving to interview phase."
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
