"""
Phase Agent - Conducts a single interview phase using LLM
"""

import logging

from google.adk.agents import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools import ToolContext

from ...shared.constants import MODEL_NAME

logger = logging.getLogger(__name__)


def mark_phase_complete(tool_context: ToolContext) -> str:
    """Mark the current phase as complete.

    Use this when the candidate has adequately covered the phase topics.

    Args:
        tool_context: Tool execution context

    Returns:
        Confirmation message
    """
    tool_context.state["phase_complete"] = True
    phase_id = tool_context.state.get("current_phase", "unknown")
    logger.info(f"Phase {phase_id} marked complete")
    return f"Phase {phase_id} marked complete. Moving to next phase."


class PhaseAgent(Agent):
    """Generic phase agent that conducts one interview phase with LLM"""

    def __init__(self, tools):
        """
        Args:
            tools: Company-specific tool provider (e.g., AmazonSystemDesignTools)
        """

        def get_phase_instruction(ctx: ReadonlyContext) -> str:
            """Generate phase-specific instruction based on current phase in session state."""
            phase_id = ctx.session.state.get("current_phase", "unknown")
            phase_context = tools.get_context(phase_id)

            return f"""You are conducting the {phase_id} phase of a system design interview.

Phase Context:
{phase_context}

Your role:
1. Ask relevant questions about the topics in this phase
2. Guide the candidate through the discussion
3. Provide hints if they're stuck
4. When the candidate has adequately covered the key topics, call mark_phase_complete()

Be conversational, encouraging, and thorough. Don't rush - let the candidate think through
the problem."""

        super().__init__(
            model=MODEL_NAME,
            name="phase_agent",
            description="Conducts a single interview phase with multi-turn conversation",
            tools=[mark_phase_complete],
            instruction=get_phase_instruction,
        )
        self.tools = tools
