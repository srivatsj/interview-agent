"""
Phase Agent - Conducts a single interview phase
"""

import logging
from typing import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions

logger = logging.getLogger(__name__)


class PhaseAgent(BaseAgent):
    """Generic phase agent that conducts one interview phase"""

    # Pydantic configuration to allow arbitrary types and extra fields
    model_config = {"arbitrary_types_allowed": True, "extra": "allow"}

    def __init__(self, tools):
        """
        Args:
            tools: Company-specific tool provider (e.g., AmazonSystemDesignTools)
        """
        super().__init__(
            name="phase_agent",
            description="Conducts a single interview phase with multi-turn conversation",
        )
        self.tools = tools

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Execute one phase iteration"""
        phase_id = ctx.session.state.get("current_phase")
        logger.info(f"PhaseAgent running for phase: {phase_id}")

        # Step 1: Show context (first time)
        if not ctx.session.state.get("context_shown"):
            logger.info(f"Showing phase context for: {phase_id}")
            yield Event(author=self.name)
            yield Event(author=self.name, actions=EventActions(state_delta={"context_shown": True}))
            return

        # Step 2: Conduct discussion (LLM handles this naturally)
        logger.info("Conducting discussion")

        # Step 3: Evaluate
        logger.info("Evaluating phase completion")

        # Placeholder decision
        phase_complete = False

        if phase_complete:
            yield Event(
                author=self.name,
                actions=EventActions(state_delta={"phase_complete": True}),
            )
        else:
            yield Event(
                author=self.name,
                actions=EventActions(state_delta={"phase_complete": False}),
            )
