"""Interview agent builder - maps interview types to agent builders."""

from google.adk.agents import Agent

from .design import build_design_agent


def build_interview_agent(interview_type: str, company: str) -> Agent:
    """Build interview agent based on type and company.

    Args:
        interview_type: Type of interview (system_design, coding)
        company: Company name (google, amazon, meta)

    Returns:
        Agent configured for interview type and company

    Raises:
        ValueError: If interview_type not supported
    """
    if interview_type == "system_design":
        return build_design_agent(company)

    raise ValueError(
        f"Unsupported interview type: {interview_type}. "
        f"Supported types: system_design"
    )
