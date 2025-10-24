"""
System Design Interview Orchestrator

Custom orchestrator with deterministic phase transitions:
intro -> design (TODO) -> closing
"""

import logging
from typing import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions

from ...shared.agents.closing_agent import closing_agent
from ...shared.agents.intro_agent import intro_agent

logger = logging.getLogger(__name__)


class SystemDesignOrchestrator(BaseAgent):
    """Custom orchestrator with state-based phase transitions"""

    # Type hints for sub-agents (required by BaseAgent)
    intro_agent: BaseAgent
    closing_agent: BaseAgent

    # Pydantic configuration to allow arbitrary types
    model_config = {"arbitrary_types_allowed": True}

    def __init__(self, intro_agent: BaseAgent, closing_agent: BaseAgent):
        # Pass sub-agents to BaseAgent constructor
        super().__init__(
            name="system_design_interview_orchestrator",
            description="Orchestrates system design interview with deterministic phase flow",
            intro_agent=intro_agent,
            closing_agent=closing_agent,
            sub_agents=[intro_agent, closing_agent],
        )

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """
        State-based flow:
        1. Check current interview_phase in state
        2. Run appropriate agent for current phase
        3. Transition to next phase
        """
        phase = ctx.session.state.get("interview_phase", "intro")
        logger.info(f"Current phase: {phase}")

        if phase == "intro":
            async for event in self.intro_agent.run_async(ctx):
                yield event

            # Check if candidate info was collected
            if "candidate_info" in ctx.session.state:
                logger.info("Candidate info collected, transitioning to closing phase")
                yield Event(
                    author=self.name,
                    actions=EventActions(state_delta={"interview_phase": "closing"}),
                )
            else:
                logger.info("Candidate info not collected yet, staying in intro phase")

        elif phase == "closing":
            async for event in self.closing_agent.run_async(ctx):
                yield event

            # Mark interview complete
            yield Event(
                author=self.name,
                actions=EventActions(state_delta={"interview_phase": "done"}),
            )

        elif phase == "done":
            logger.info("Interview already completed")


# Create instance with sub-agents
system_design_interview_orchestrator = SystemDesignOrchestrator(
    intro_agent=intro_agent,
    closing_agent=closing_agent,
)
