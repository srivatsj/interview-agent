"""
System Design Interview Orchestrator

Custom orchestrator with deterministic phase transitions:
intro -> design (TODO) -> closing
"""

from typing import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event

from ...shared.agents.closing_agent import closing_agent
from ...shared.agents.intro_agent import intro_agent


class SystemDesignOrchestrator(BaseAgent):
    """Custom orchestrator with state-based phase transitions"""

    def __init__(self):
        super().__init__(
            name="system_design_interview_orchestrator",
            description="Orchestrates system design interview with deterministic phase flow",
        )
        self._intro_agent = intro_agent
        self._closing_agent = closing_agent

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """
        State-based flow:
        1. Check current interview_phase in state
        2. Run appropriate agent for current phase
        3. Transition to next phase
        """
        phase = ctx.session.state.get("interview_phase", "intro")

        if phase == "intro":
            # Run intro agent
            async for event in self._intro_agent._run_async_impl(ctx):
                yield event
            # Transition to closing (design agent not implemented yet)
            ctx.session.state["interview_phase"] = "closing"

        elif phase == "closing":
            # Run closing agent
            async for event in self._closing_agent._run_async_impl(ctx):
                yield event
            # Mark interview complete
            ctx.session.state["interview_phase"] = "done"

        elif phase == "done":
            # Interview already completed
            yield Event.create("Interview session completed. Thank you!")


# Create instance
system_design_interview_orchestrator = SystemDesignOrchestrator()
