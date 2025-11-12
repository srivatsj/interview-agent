"""Root Agent - Coordinator with Sub-Agents.

Uses sub-agents for each interview phase.
Phase flow: routing → intro → interview → closing → done
"""

import logging
import os

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.agents.readonly_context import ReadonlyContext

from .agents.closing import closing_agent
from .agents.interview import interview_agent
from .agents.intro import intro_agent
from .agents.routing import routing_agent

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


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
        return "TRANSFER to interview_agent immediately."
    elif phase == "closing":
        return "TRANSFER to closing_agent immediately."
    else:  # done
        return "Session complete. Say goodbye!"


# Root coordinator agent
root_agent = Agent(
    name="interview_coordinator",
    model=os.getenv("AGENT_MODEL", "gemini-2.0-flash-exp"),
    description="Interview coordinator managing interview flow",
    instruction=_get_coordinator_instruction,
    sub_agents=[routing_agent, intro_agent, interview_agent, closing_agent],
    tools=[],
)
