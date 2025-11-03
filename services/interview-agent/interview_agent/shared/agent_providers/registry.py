"""A2A Provider Registry for remote interview agents.

Maps companies/interview types to remote agent endpoints.
Also provides fallback local options when no remote agents are configured.
"""

import logging
import os
from dataclasses import dataclass, field

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Free default agents available to all users
# These are user-selectable options alongside remote agents
# Remote agents (google, meta, etc.) may incur costs, but default agents are always free
DEFAULT_AGENTS = {
    "default": ["system_design"],
}



@dataclass
class RemoteAgentConfig:
    """Configuration for a remote interview agent."""

    url: str
    description: str
    supported_types: list[str] = field(default_factory=list)


class AgentProviderRegistry:
    """Registry of remote interview agents accessible via A2A protocol.

    Configuration is read from environment variables:
    - INTERVIEW_AGENTS: Comma-separated list of agent names (optional)
      - If not set, runs in local-only mode (no remote agents)
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

    Example (local-only mode):
        # Don't set INTERVIEW_AGENTS - will use local tools only

    Raises:
        ValueError: If INTERVIEW_AGENTS is set but required env vars are missing
    """

    @classmethod
    def _load_agents(cls) -> dict[str, RemoteAgentConfig]:
        """Load agent configuration from environment variables.

        Returns:
            Dict mapping company name to RemoteAgentConfig.
            Returns empty dict if INTERVIEW_AGENTS is not set (allows local-only mode).

        Raises:
            ValueError: If INTERVIEW_AGENTS is set but required env vars are missing
        """
        # Get list of agents to configure
        agents_str = os.getenv("INTERVIEW_AGENTS")
        if not agents_str:
            # No remote agents configured - return empty dict (allows local fallback)
            logger.info("INTERVIEW_AGENTS not set - running in local-only mode")
            return {}

        agent_names = [name.strip() for name in agents_str.split(",") if name.strip()]
        if not agent_names:
            logger.warning("INTERVIEW_AGENTS is empty - running in local-only mode")
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

    _DEFAULT_AGENTS = None

    @classmethod
    def _get_agents(cls) -> dict[str, RemoteAgentConfig]:
        """Get agents, loading from env on first access."""
        if cls._DEFAULT_AGENTS is None:
            cls._DEFAULT_AGENTS = cls._load_agents()
        return cls._DEFAULT_AGENTS

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

        Includes both remote agents (from env) and free default agents.

        Returns:
            Dict mapping company name to sorted list of supported interview types

        Example:
            {"default": ["system_design"], "google": ["coding", "system_design"],
             "meta": ["system_design"]}
        """
        # Start with remote agents
        agents = cls._get_agents()
        options = {company: sorted(config.supported_types) for company, config in agents.items()}

        # Add free default agents (always available, even if not from remote)
        for company, types in DEFAULT_AGENTS.items():
            if company not in options:
                options[company] = sorted(types)

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

        Checks both remote agents and local fallback options.

        Args:
            company: Company name
            interview_type: Interview type

        Returns:
            True if the combination is supported (remote or local), False otherwise
        """
        options = cls.get_available_options()
        return company.lower() in options and interview_type.lower() in options[company.lower()]
