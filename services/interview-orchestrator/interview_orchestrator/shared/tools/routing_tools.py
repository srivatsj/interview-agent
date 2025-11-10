"""Tools for interview routing phase.

Determines company and interview type.
"""

import logging

from google.adk.tools import ToolContext

from ..agent_providers import AgentProviderRegistry
from ..schemas import RoutingDecision

logger = logging.getLogger(__name__)


def set_routing_decision(
    company: str,
    interview_type: str,
    tool_context: ToolContext,
) -> str:
    """Save the routing decision and begin the interview.

    Use this when you've determined which company and interview type the user wants.

    Args:
        company: The company (google, meta, amazon, etc.)
        interview_type: The interview type (system_design, coding, or behavioral)
        tool_context: Tool execution context

    Returns:
        Confirmation message or error if combination is invalid
    """
    # Validate using registry
    if not AgentProviderRegistry.is_valid_combination(company, interview_type):
        available = AgentProviderRegistry.get_formatted_options()
        return (
            f"Error: '{company} {interview_type}' is not available.\n\n"
            f"Available options:\n{available}"
        )

    routing_decision = RoutingDecision(
        company=company.lower(),
        interview_type=interview_type.lower(),
        confidence=1.0,
    )

    # Save to session state and transition to intro
    tool_context.state["routing_decision"] = routing_decision.model_dump()
    tool_context.state["interview_phase"] = "intro"

    logger.info(f"Routing decision saved: {company.lower()} {interview_type.lower()}")

    return (
        f"Routing saved: {company.lower()} {interview_type.lower()}. "
        "Starting interview intro phase."
    )
