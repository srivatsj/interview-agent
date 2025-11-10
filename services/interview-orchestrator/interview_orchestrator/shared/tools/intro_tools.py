"""Tools for interview intro phase.

Collects candidate background information.
"""

from google.adk.tools import ToolContext

from ..schemas import CandidateInfo


def save_candidate_info(
    name: str,
    years_experience: int,
    domain: str,
    projects: str,
    tool_context: ToolContext,
) -> str:
    """Save candidate background information and transition to design phase.

    Use this after collecting all required candidate information:
    - Full name
    - Years of professional experience
    - Primary technical domain/expertise
    - Notable projects they've worked on

    This will automatically move the interview to the design phase.

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

    # Save to session state
    tool_context.state["candidate_info"] = candidate_info.model_dump()
    tool_context.state["interview_phase"] = "design"

    return (
        f"Candidate info saved: {name}, {years_experience} years experience "
        f"in {domain}. Moving to design phase."
    )
