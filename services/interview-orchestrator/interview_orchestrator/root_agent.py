"""Root Agent - Coordinator with Dynamic Sub-Agents.

Uses sub-agents for each interview phase with dynamic interview agent selection.
Phase flow: routing → intro → interview → closing → done
"""

import logging
import os

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.agents.readonly_context import ReadonlyContext

from .agents.closing import closing_agent
from .agents.interview_types.builder import build_interview_agent
from .agents.intro import intro_agent
from .agents.routing import routing_agent

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


def _get_dynamic_sub_agents(ctx: ReadonlyContext) -> list[Agent]:
    """Build sub-agents list with dynamic interview agent.

    Returns:
        List of sub-agents with interview agent selected based on state
    """
    phase = ctx.session.state.get("interview_phase", "routing")

    base_agents = [routing_agent, intro_agent, closing_agent]

    # Add interview agent dynamically when in interview phase
    if phase == "interview":
        routing = ctx.session.state.get("routing_decision", {})
        company = routing["company"]
        interview_type = routing["interview_type"]

        try:
            interview_agent = build_interview_agent(interview_type, company)
            base_agents.insert(2, interview_agent)
        except ValueError as e:
            logger.error(f"Failed to build interview agent: {e}")
            raise

    return base_agents


def _get_coordinator_instruction(ctx: ReadonlyContext) -> str:
    """State-based coordinator instruction.

    Deterministic routing based on interview_phase state.
    """
    phase = ctx.session.state.get("interview_phase", "routing")

    if phase == "routing":
        return "TRANSFER to routing_agent immediately."
    elif phase == "intro":
        return "TRANSFER to intro_agent immediately."
    elif phase == "interview":
        routing = ctx.session.state.get("routing_decision", {})
        interview_type = routing.get("interview_type", "interview")
        agent_name = f"{interview_type}_agent"
        return f"TRANSFER to {agent_name} immediately."
    elif phase == "closing":
        return "TRANSFER to closing_agent immediately."
    else:  # done
        return "Session complete. Say goodbye!"


# Root coordinator agent
root_agent = Agent(
    name="interview_coordinator",
    model=os.getenv("AGENT_MODEL", "gemini-2.0-flash-exp"),
    description="Interview coordinator with dynamic sub-agents",
    instruction=_get_coordinator_instruction,
    sub_agents=_get_dynamic_sub_agents,
    tools=[],
)
