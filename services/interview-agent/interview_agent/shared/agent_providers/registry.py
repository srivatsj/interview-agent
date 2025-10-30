"""A2A Provider Registry for remote interview agents.

Maps companies/interview types to remote agent endpoints.
"""

import logging
import os
from dataclasses import dataclass

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


@dataclass
class RemoteAgentConfig:
    """Configuration for a remote interview agent."""

    url: str
    interview_type: str
    description: str


class AgentProviderRegistry:
    """Registry of remote interview agents accessible via A2A protocol."""

    # Default agent endpoints (can be overridden via environment variables)
    _DEFAULT_AGENTS = {
        "google": RemoteAgentConfig(
            url="http://localhost:10123",
            interview_type="system_design",
            description="Google-style system design interviewer",
        ),
        "meta": RemoteAgentConfig(
            url="http://localhost:10125",
            interview_type="system_design",
            description="Meta-style system design interviewer using LangGraph",
        ),
    }

    @classmethod
    def get_agent_url(cls, company: str, interview_type: str) -> str | None:
        """Get remote agent URL for a company and interview type.

        Args:
            company: Company name (e.g., 'google', 'meta')
            interview_type: Interview type (e.g., 'system_design', 'coding')

        Returns:
            Agent URL if found, None otherwise
        """
        # Check environment variable override
        env_key = f"{company.upper()}_{interview_type.upper()}_AGENT_URL"
        env_url = os.getenv(env_key)
        if env_url:
            logger.info(f"Using {env_key}={env_url}")
            return env_url

        # Check default registry
        agent_config = cls._DEFAULT_AGENTS.get(company.lower())
        if agent_config and agent_config.interview_type == interview_type.lower():
            return agent_config.url

        return None

    @classmethod
    def list_available_agents(cls) -> dict[str, RemoteAgentConfig]:
        """List all registered remote agents."""
        return cls._DEFAULT_AGENTS.copy()
