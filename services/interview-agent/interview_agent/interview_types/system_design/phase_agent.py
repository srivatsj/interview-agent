"""
Phase Agent - Conducts a single interview phase using LLM
"""

import logging

from google.adk.agents import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools import ToolContext

from ...shared.constants import MODEL_NAME
from ...shared.prompts.prompt_loader import load_prompt

logger = logging.getLogger(__name__)


class PhaseAgent(Agent):
    """Generic phase agent that conducts one interview phase with LLM"""

    # Pydantic configuration to allow extra fields
    model_config = {"extra": "allow"}

    @staticmethod
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

    def __init__(self, tool_provider):
        """
        Args:
            tool_provider: Company-specific tool provider (e.g., AmazonSystemDesignTools)
        """
        super().__init__(
            model=MODEL_NAME,
            name="phase_agent",
            description="Conducts a single interview phase with multi-turn conversation",
            tools=[PhaseAgent.mark_phase_complete],
            instruction=self._get_phase_instruction,
        )
        self.tool_provider = tool_provider

    def _get_phase_instruction(self, ctx: ReadonlyContext) -> str:
        """Generate phase-specific instruction based on current phase in session state.

        Args:
            ctx: Readonly context containing session state

        Returns:
            Instruction string for the current phase
        """
        phase_id = ctx.session.state.get("current_phase", "unknown")
        phase_context = self.tool_provider.get_context(phase_id)

        # Load template and substitute phase-specific values
        template = load_prompt("phase_agent.txt")
        return template.replace("{phase_id}", phase_id).replace("{phase_context}", phase_context)
