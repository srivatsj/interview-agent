"""Routing agent for company and interview type selection."""

import logging
import os

from google.adk.agents import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools import ToolContext

from ..shared.agent_registry import AgentProviderRegistry
from ..shared.prompts.prompt_loader import load_prompt
from ..shared.schemas.routing_decision import RoutingDecision

logger = logging.getLogger(__name__)


def set_routing_decision(
    company: str,
    interview_type: str,
    tool_context: ToolContext,
) -> str:
    """Save the routing decision and begin the interview.

    Args:
        company: The company (google, meta, amazon, etc.)
        interview_type: The interview type (system_design, coding, or behavioral)
        tool_context: Tool execution context

    Returns:
        Confirmation message or error if combination is invalid
    """
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

    tool_context.state["routing_decision"] = routing_decision.model_dump()
    tool_context.state["interview_phase"] = "intro"

    logger.info(f"Routing decision saved: {company.lower()} {interview_type.lower()}")

    return (
        f"Routing saved: {company.lower()} {interview_type.lower()}. "
        "Starting interview intro phase."
    )


def get_routing_instruction(ctx: ReadonlyContext) -> str:
    """Get routing instruction with available options."""
    return load_prompt(
        "routing_agent.txt",
        available_options=AgentProviderRegistry.get_formatted_options(),
    )


routing_agent = Agent(
    name="routing_agent",
    model=os.getenv("AGENT_MODEL", "gemini-2.0-flash-exp"),
    description="Helps user choose company and interview type",
    instruction=get_routing_instruction,
    tools=[set_routing_decision],
)
