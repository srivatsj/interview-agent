"""
System Design Interview Orchestrator
"""

import logging
from typing import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions

from .phase_agent import PhaseAgent

logger = logging.getLogger(__name__)


class SystemDesignAgent(BaseAgent):
    """Orchestrates system design interview with multiple phases"""

    # Pydantic configuration to allow arbitrary types and extra fields
    model_config = {"arbitrary_types_allowed": True, "extra": "allow"}

    def __init__(self, tool_provider, name: str = "system_design_orchestrator"):
        """
        Args:
            tool_provider: Company-specific tool provider (e.g., AmazonSystemDesignTools)
            name: Agent name (default: "system_design_orchestrator")
        """
        logger.info(f"Initializing SystemDesignAgent with name: {name}")

        # Fetch phases from tools
        phases = tool_provider.get_phases()

        # Create phase agent
        phase_agent = PhaseAgent(tool_provider)

        super().__init__(
            name=name,
            description="Conducts system design interview with phase orchestration",
            sub_agents=[phase_agent],
        )

        # Set attributes after super().__init__()
        self.tool_provider = tool_provider
        self.phases = phases
        self.phase_agent = phase_agent

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Orchestrate interview phases with clean phase sequencing"""
        phase_idx = ctx.session.state.get("current_phase_idx", 0)

        # Check if all phases complete
        if phase_idx >= len(self.phases):
            logger.info("All interview phases complete")
            yield Event(
                author=self.name,
                actions=EventActions(state_delta={"interview_phases_complete": True}),
            )
            return

        # Setup current phase
        current_phase = self.phases[phase_idx]
        logger.info(f"Starting phase {phase_idx + 1}/{len(self.phases)}: {current_phase['name']}")

        # Initialize phase state
        yield Event(
            author=self.name,
            actions=EventActions(
                state_delta={
                    "current_phase": current_phase["id"],
                    "current_phase_idx": phase_idx,
                    "phase_complete": False,
                }
            ),
        )

        # Run phase agent (loops internally until phase complete)
        async for event in self.phase_agent.run_async(ctx):
            yield event

        # Phase agent has exited loop - phase is complete
        logger.info(f"Phase {current_phase['name']} complete, advancing to next phase")
        yield Event(
            author=self.name,
            actions=EventActions(state_delta={"current_phase_idx": phase_idx + 1}),
        )
