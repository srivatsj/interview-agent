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

    def __init__(self, company: str):
        """
        Args:
            company: Company name (e.g., "amazon", "google", "meta")
        """
        logger.info(f"Initializing SystemDesignAgent for company: {company}")

        # Get company-specific tools
        tools = self._get_company_tools(company)

        # Fetch phases from tools
        phases = self._fetch_phases()

        # Create phase agent
        phase_agent = PhaseAgent(tools)

        super().__init__(
            name=f"{company}_system_design_orchestrator",
            description=f"Conducts system design interview for {company}",
            sub_agents=[phase_agent],
        )

        # Set attributes after super().__init__()
        self.tools = tools
        self.phases = phases
        self.phase_agent = phase_agent

    def _get_company_tools(self, company: str):
        """Inject company-specific tool provider"""
        logger.info(f"Loading tools for company: {company}")

        if company == "amazon":
            # TODO: Import and instantiate company-specific tools
            # from .companies.amazon_tools import AmazonSystemDesignTools
            # return AmazonSystemDesignTools()
            return None  # Placeholder
        elif company == "google":
            return None  # Placeholder
        else:
            raise ValueError(f"Unknown company: {company}")

    def _fetch_phases(self) -> list[dict]:
        """Fetch interview phases from tools"""
        logger.info("Fetching interview phases")

        # TODO: Call tools.get_phases() synchronously
        # Placeholder phases for now
        return [
            {"id": "problem_clarification", "name": "Problem Clarification"},
            {"id": "requirements", "name": "Requirements"},
            {"id": "data_design", "name": "Data Design"},
            {"id": "api_design", "name": "API Design"},
            {"id": "hld", "name": "High Level Design"},
        ]

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Orchestrate interview phases"""
        phase_idx = ctx.session.state.get("current_phase_idx", 0)

        # Check if interview complete
        if phase_idx >= len(self.phases):
            logger.info("Interview complete")
            yield Event(author=self.name)
            return

        # Setup current phase
        current_phase = self.phases[phase_idx]
        logger.info(f"Starting phase {phase_idx + 1}/{len(self.phases)}: {current_phase['name']}")

        ctx.session.state["current_phase"] = current_phase["id"]
        ctx.session.state["phase_complete"] = False
        ctx.session.state["context_shown"] = False

        # Run phase agent
        async for event in self.phase_agent.run_async(ctx):
            yield event

        # Move to next phase
        logger.info(f"Phase {current_phase['name']} complete, moving to next")
        yield Event(
            author=self.name,
            actions=EventActions(state_delta={"current_phase_idx": phase_idx + 1}),
        )
