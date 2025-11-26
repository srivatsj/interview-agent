"""A2A Provider Registry for remote interview agents.

Maps companies/interview types to remote agent endpoints.
"""

import logging
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

# Load environment variables (don't override existing env vars from tests)
load_dotenv(override=False)

logger = logging.getLogger(__name__)


@dataclass
class RemoteAgentConfig:
    """Configuration for a remote interview agent."""

    url: str
    description: str
    supported_types: list[str] = field(default_factory=list)


class AgentProviderRegistry:
    """Registry of remote interview agents accessible via A2A protocol.

    Configuration is read from environment variables:
    - INTERVIEW_AGENTS: Comma-separated list of agent names
    - For each agent: {AGENT_NAME}_AGENT_URL (required if agent is listed)
    - For each agent: {AGENT_NAME}_AGENT_TYPES (required if agent is listed)
    - For each agent: {AGENT_NAME}_AGENT_DESCRIPTION (optional)

    Example (with remote agents):
        INTERVIEW_AGENTS=google,meta
        GOOGLE_AGENT_URL=http://localhost:10123
        GOOGLE_AGENT_TYPES=system_design,coding
        GOOGLE_AGENT_DESCRIPTION=Google-style interviewer
        META_AGENT_URL=http://localhost:10125
        META_AGENT_TYPES=system_design
        META_AGENT_DESCRIPTION=Meta-style interviewer

    Raises:
        ValueError: If INTERVIEW_AGENTS is set but required env vars are missing
    """

    @classmethod
    def _load_agents(cls) -> dict[str, RemoteAgentConfig]:
        """Load agent configuration from environment variables.

        Returns:
            Dict mapping company name to RemoteAgentConfig.
            Returns empty dict if INTERVIEW_AGENTS is not set.

        Raises:
            ValueError: If INTERVIEW_AGENTS is set but required env vars are missing
        """
        # Get list of agents to configure
        agents_str = os.getenv("INTERVIEW_AGENTS")
        if not agents_str:
            logger.info("INTERVIEW_AGENTS not set - no remote agents configured")
            return {}

        agent_names = [name.strip() for name in agents_str.split(",") if name.strip()]
        if not agent_names:
            logger.warning("INTERVIEW_AGENTS is empty - no remote agents configured")
            return {}

        agents = {}
        for agent_name in agent_names:
            agent_upper = agent_name.upper()
            url_key = f"{agent_upper}_AGENT_URL"
            types_key = f"{agent_upper}_AGENT_TYPES"
            desc_key = f"{agent_upper}_AGENT_DESCRIPTION"

            url = os.getenv(url_key)
            types_str = os.getenv(types_key)
            description = os.getenv(desc_key, f"{agent_name.title()}-style interviewer")

            if not url:
                raise ValueError(f"Missing required environment variable: {url_key}")
            if not types_str:
                raise ValueError(f"Missing required environment variable: {types_key}")

            agents[agent_name.lower()] = RemoteAgentConfig(
                url=url,
                description=description,
                supported_types=[t.strip() for t in types_str.split(",") if t.strip()],
            )

        return agents

    _agents_cache = None

    @classmethod
    def _get_agents(cls) -> dict[str, RemoteAgentConfig]:
        """Get agents, loading from env on first access."""
        if cls._agents_cache is None:
            cls._agents_cache = cls._load_agents()
        return cls._agents_cache

    @classmethod
    def get_agent_url(cls, company: str, interview_type: str) -> str | None:
        """Get remote agent URL for a company and interview type.

        Args:
            company: Company name (e.g., 'google', 'meta')
            interview_type: Interview type (e.g., 'system_design', 'coding')

        Returns:
            Agent URL if found and supports the interview type, None otherwise
        """
        agents = cls._get_agents()
        agent_config = agents.get(company.lower())
        if agent_config and interview_type.lower() in agent_config.supported_types:
            return agent_config.url
        return None

    @classmethod
    def get_available_options(cls) -> dict[str, list[str]]:
        """Get all available interview options organized by company.

        Returns:
            Dict mapping company name to sorted list of supported interview types

        Example:
            {"google": ["coding", "system_design"], "meta": ["system_design"]}
        """
        agents = cls._get_agents()
        options = {company: sorted(config.supported_types) for company, config in agents.items()}
        return dict(sorted(options.items()))

    @classmethod
    def get_formatted_options(cls) -> str:
        """Get formatted string of available options for display.

        Returns:
            Formatted string with one option per line, sorted by company then type

        Example:
            "- Google coding\\n- Google system_design\\n- Meta system_design"
        """
        options = cls.get_available_options()
        lines = []
        for company, types in options.items():
            for interview_type in types:
                lines.append(f"- {company.title()} {interview_type}")
        return "\n".join(lines)

    @classmethod
    def is_valid_combination(cls, company: str, interview_type: str) -> bool:
        """Check if a company/interview_type combination is valid.

        Args:
            company: Company name
            interview_type: Interview type

        Returns:
            True if the combination is supported, False otherwise
        """
        options = cls.get_available_options()
        return company.lower() in options and interview_type.lower() in options[company.lower()]
