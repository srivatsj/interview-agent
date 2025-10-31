"""Factory for creating interview orchestrators based on type and company."""

import logging

from google.adk.agents import BaseAgent

from ...interview_types.system_design.orchestrator import SystemDesignOrchestrator
from ...interview_types.system_design.system_design_agent import SystemDesignAgent
from ..agents.closing_agent import create_closing_agent
from ..agents.intro_agent import create_intro_agent
from .company_factory import CompanyFactory

logger = logging.getLogger(__name__)


class InterviewFactory:
    """Factory for creating interview orchestrators."""

    @staticmethod
    def create_interview_orchestrator(routing_decision: dict) -> BaseAgent:
        """Create an interview orchestrator based on routing decision.

        Args:
            routing_decision: Dict with 'interview_type' and 'company' keys

        Returns:
            Interview orchestrator

        Raises:
            ValueError: If interview_type or company is missing or invalid
            NotImplementedError: If interview type is not yet implemented
        """
        interview_type = routing_decision.get("interview_type", "")
        company = routing_decision.get("company", "")

        if not interview_type:
            raise ValueError("Missing 'interview_type' in routing decision")

        if not company:
            raise ValueError("Missing 'company' in routing decision")

        interview_type_lower = interview_type.lower()
        company_lower = company.lower()

        if interview_type_lower == "system_design":
            return InterviewFactory._create_system_design_orchestrator(
                company_lower, interview_type_lower
            )
        elif interview_type_lower == "coding":
            raise NotImplementedError("Coding interviews not yet implemented")
        elif interview_type_lower == "behavioral":
            raise NotImplementedError("Behavioral interviews not yet implemented")
        else:
            raise ValueError(
                f"Unknown interview type: {interview_type}. "
                "Must be one of: system_design, coding, behavioral"
            )

    @staticmethod
    def _create_system_design_orchestrator(
        company: str, interview_type: str
    ) -> SystemDesignOrchestrator:
        """Create system design orchestrator with company-specific agent.

        Args:
            company: Company name
            interview_type: Interview type

        Returns:
            SystemDesignOrchestrator with company-specific design agent
        """
        # Get company-specific tools
        tool_provider = CompanyFactory.get_tools(company, interview_type)

        # Create design agent with tools
        design_agent = SystemDesignAgent(
            tool_provider=tool_provider,
            name=f"{company}_system_design_orchestrator",
        )

        # Create new agent instances to avoid parent conflicts
        return SystemDesignOrchestrator(
            intro_agent=create_intro_agent(),
            design_agent=design_agent,
            closing_agent=create_closing_agent(),
        )
