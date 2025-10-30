"""Factory for creating company-specific system design agents via A2A protocol."""

import logging

from ..agent_providers import (
    AgentProviderRegistry,
    InterviewAgentProtocol,
    LocalAgentProvider,
    RemoteAgentProvider,
)
from ...interview_types.system_design.tools import DefaultSystemDesignTools

logger = logging.getLogger(__name__)


class CompanyFactory:
    """Factory for creating company-specific design agents.

    Returns clients conforming to InterviewAgentProtocol - either remote A2A agents
    or local tool providers wrapped in LocalAgentClient.
    """

    @staticmethod
    def get_tools(company: str, interview_type: str) -> InterviewAgentProtocol:
        """Get company-specific interview agent (remote or local).

        Args:
            company: Company name (google, meta, acme, etc.)
            interview_type: Interview type (e.g., 'system_design', 'coding')

        Returns:
            Provider conforming to InterviewAgentProtocol
            (RemoteAgentProvider for remote agents, LocalAgentProvider for default tools)

        Raises:
            ValueError: If company is not supported and has no remote agent
        """
        company_lower = company.lower()
        logger.info(f"Loading agent for company: {company_lower}, type: {interview_type}")

        # Check for remote A2A agent first
        agent_url = AgentProviderRegistry.get_agent_url(company_lower, interview_type)
        if agent_url:
            logger.info(f"Using remote agent at {agent_url}")
            return RemoteAgentProvider(agent_url=agent_url)

        # Fallback to default local tools
        logger.info(f"No remote agent found, using default local tools for {company_lower}")
        return LocalAgentProvider(DefaultSystemDesignTools())
