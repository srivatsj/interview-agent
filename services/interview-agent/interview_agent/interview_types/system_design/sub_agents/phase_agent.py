"""Phase Agent - Conducts interview phase with LoopAgent pattern"""

import logging
from typing import AsyncGenerator

from google.adk.agents import Agent, BaseAgent, LoopAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event

from ....shared.constants import MODEL_NAME
from ....shared.prompts.prompt_loader import load_prompt
from .completion_checker import PhaseCompletionChecker

logger = logging.getLogger(__name__)


class PhaseAgent(BaseAgent):
    """Loop-based phase agent using ADK LoopAgent pattern."""

    model_config = {"arbitrary_types_allowed": True, "extra": "allow"}

    def __init__(self, tool_provider, max_turns: int = 10):
        """
        Args:
            tool_provider: Company-specific tool provider
            max_turns: Maximum turns before forcing exit (default: 10)
        """
        super().__init__(
            name="phase_agent",
            description="Conducts interview phase with automatic evaluation-based completion",
        )
        self.tool_provider = tool_provider
        self.max_turns = max_turns

    async def _get_phase_instruction(self, phase_id: str) -> str:
        """Generate phase-specific instruction.

        Args:
            phase_id: Current phase ID

        Returns:
            Instruction string for the phase
        """
        phase_context = await self.tool_provider.get_context(phase_id)
        return load_prompt("phase_agent.txt", phase_id=phase_id, phase_context=phase_context)

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Create and run LoopAgent for this phase.

        Flow:
        1. Get phase from state
        2. Create conversation agent with phase context
        3. Create completion checker
        4. Wrap in LoopAgent that runs until checker escalates
        """
        phase_id = ctx.session.state.get("current_phase", "unknown")
        logger.info(f"PhaseAgent starting loop for phase: {phase_id}")

        # Reset turn count
        ctx.session.state["phase_turn_count"] = 0

        # Create instruction
        instruction = await self._get_phase_instruction(phase_id)

        # Create conversation agent
        conversation_agent = Agent(
            model=MODEL_NAME,
            name=f"phase_{phase_id}_conversation",
            description=f"Conducts {phase_id} phase conversation",
            tools=[],
            instruction=instruction,
        )

        # Create completion checker
        completion_checker = PhaseCompletionChecker(self.tool_provider)

        # Create loop agent
        loop_agent = LoopAgent(
            name=f"phase_{phase_id}_loop",
            description=f"Loops {phase_id} phase until completion",
            sub_agents=[conversation_agent, completion_checker],
            max_iterations=self.max_turns,
        )

        # Run loop
        async for event in loop_agent.run_async(ctx):
            yield event

        logger.info(f"PhaseAgent completed loop for phase: {phase_id}")
