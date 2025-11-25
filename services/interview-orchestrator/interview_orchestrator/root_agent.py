"""Root Agent - Coordinator with Sub-Agents.

Uses sub-agents for each interview phase.
Phase flow: routing → intro → interview → closing → done
"""

import logging

from dotenv import load_dotenv

# Load environment variables BEFORE importing anything that uses them
# override=False: Don't override existing env vars (allows tests to set ENV=test)
load_dotenv(override=False)

from google.adk.agents import Agent
from google.adk.agents.readonly_context import ReadonlyContext

from .agents.closing import closing_agent
from .agents.interview import interview_agent
from .agents.intro import intro_agent
from .agents.routing import routing_agent
from .shared.constants import get_gemini_model

logger = logging.getLogger(__name__)


def _get_coordinator_instruction(ctx: ReadonlyContext) -> str:
    """State-based coordinator instruction.

    Deterministic routing based on interview_phase state.
    """
    phase = ctx.session.state.get("interview_phase", "routing")
    logger.info(f"🎯 COORDINATOR: Current phase = '{phase}', routing to appropriate agent")

    if phase == "routing":
        logger.info("🎯 COORDINATOR: Transferring to routing_agent")
        return (
            "The user has started the conversation. TRANSFER to routing_agent "
            "immediately, using the 'transfer_to_agent' tool, to begin the interview."
        )
    elif phase == "intro":
        logger.info("🎯 COORDINATOR: Transferring to intro_agent")
        return "TRANSFER to intro_agent immediately."
    elif phase == "interview":
        logger.info("🎯 COORDINATOR: Transferring to interview_agent")
        return "TRANSFER to interview_agent immediately."
    elif phase == "closing":
        logger.info("🎯 COORDINATOR: Transferring to closing_agent")
        return "TRANSFER to closing_agent immediately."
    else:  # done
        logger.info("🎯 COORDINATOR: Session complete")
        return "Session complete. Say goodbye!"


# Root coordinator agent
root_agent = Agent(
    name="interview_coordinator",
    model=get_gemini_model(),
    description="Interview coordinator managing interview flow",
    global_instruction=(
        "You are an interview coordinator. Guide candidates through their "
        "technical interview practice session."
    ),
    instruction=_get_coordinator_instruction,
    sub_agents=[routing_agent, intro_agent, interview_agent, closing_agent],
    tools=[],
)
