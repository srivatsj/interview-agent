"""Design interview tools for system design interviews.

Provides tools for initializing and completing design phase.
"""

import logging

from google.adk.tools import ToolContext

from ...shared.factories import CompanyFactory

logger = logging.getLogger(__name__)


async def initialize_design_phase(tool_context: ToolContext) -> str:
    """Initialize design phase by fetching interview question.

    Loads the company-specific interview question and prepares for design discussion.
    Call this when transitioning from intro to design phase.

    Returns:
        Confirmation message with question preview
    """
    # Get routing and candidate info from state
    routing = tool_context.state.get("routing_decision", {})
    candidate_info = tool_context.state.get("candidate_info", {})

    company = routing.get("company", "default")
    interview_type = routing.get("interview_type", "system_design")

    logger.info(f"Initializing design phase: {company} {interview_type}")

    # Get company-specific provider (remote or local)
    provider = CompanyFactory.get_tools(company, interview_type)

    # Initialize interview session
    await provider.start_interview(interview_type, candidate_info)

    # Fetch and store interview question
    question = await provider.get_question()
    tool_context.state["interview_question"] = question

    logger.info(f"Design question loaded: {question[:100]}...")

    return f"Design phase initialized. Question ready: {question[:100]}..."


def mark_design_complete(tool_context: ToolContext) -> str:
    """Mark design phase as complete and transition to closing.

    Call this when the candidate has thoroughly discussed the design question
    and you've covered all important aspects.

    Returns:
        Confirmation message
    """
    tool_context.state["design_complete"] = True
    tool_context.state["interview_phase"] = "closing"

    logger.info("Design phase marked complete, transitioning to closing")

    return "Design phase complete. Moving to closing remarks."
