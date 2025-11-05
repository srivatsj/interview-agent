"""Tests for CompanyFactory A2A routing and fallback behavior."""

from unittest.mock import patch

import pytest

from interview_orchestrator.shared.agent_providers import LocalAgentProvider, RemoteAgentProvider
from interview_orchestrator.shared.factories import CompanyFactory


class TestCompanyFactoryBasic:
    """Basic CompanyFactory functionality tests."""

    def test_get_tools_google_remote_agent(self):
        """Test that google returns RemoteAgentProvider with correct URL."""
        tools = CompanyFactory.get_tools("google", "system_design")

        assert isinstance(tools, RemoteAgentProvider)
        assert tools.agent_url == "http://localhost:10123"

    def test_get_tools_meta_remote_agent(self):
        """Test that meta returns RemoteAgentProvider with correct URL."""
        tools = CompanyFactory.get_tools("meta", "system_design")

        assert isinstance(tools, RemoteAgentProvider)
        assert tools.agent_url == "http://localhost:10125"

    def test_get_tools_case_insensitive(self):
        """Test that company name is case insensitive for remote agents."""
        tools_upper = CompanyFactory.get_tools("GOOGLE", "system_design")
        tools_lower = CompanyFactory.get_tools("google", "system_design")
        tools_mixed = CompanyFactory.get_tools("Google", "system_design")

        assert isinstance(tools_upper, RemoteAgentProvider)
        assert isinstance(tools_lower, RemoteAgentProvider)
        assert isinstance(tools_mixed, RemoteAgentProvider)

    @pytest.mark.asyncio
    async def test_get_tools_default_fallback(self):
        """Test that unknown company falls back to default local tools."""
        tools = CompanyFactory.get_tools("unknown_company", "system_design")

        assert isinstance(tools, LocalAgentProvider)
        phases = await tools.get_phases()
        assert len(phases) == 5

    def test_get_tools_acme_fallback(self):
        """Test that acme (placeholder) falls back to default tools."""
        tools = CompanyFactory.get_tools("acme", "system_design")

        assert isinstance(tools, LocalAgentProvider)


class TestCompanyFactoryA2ARouting:
    """Advanced A2A routing tests with mocking."""

    @patch(
        "interview_orchestrator.shared.factories.company_factory.AgentProviderRegistry.get_agent_url"
    )
    def test_get_tools_remote_agent_priority(self, mock_get_agent_url):
        """Test that remote agent is checked first before fallback."""
        # Simulate remote agent available for amazon
        mock_get_agent_url.return_value = "http://custom-amazon:8080"

        tools = CompanyFactory.get_tools("amazon", "system_design")

        # Should return RemoteAgentProvider
        assert isinstance(tools, RemoteAgentProvider)
        assert tools.agent_url == "http://custom-amazon:8080"
        mock_get_agent_url.assert_called_once_with("amazon", "system_design")

    @patch(
        "interview_orchestrator.shared.factories.company_factory.AgentProviderRegistry.get_agent_url"
    )
    def test_get_tools_fallback_when_no_remote(self, mock_get_agent_url):
        """Test that default tools are used when no remote agent exists."""
        # Simulate no remote agent available
        mock_get_agent_url.return_value = None

        tools = CompanyFactory.get_tools("amazon", "system_design")

        # Should fall back to default tools wrapped in LocalAgentProvider
        assert isinstance(tools, LocalAgentProvider)
        mock_get_agent_url.assert_called_once_with("amazon", "system_design")

    @patch(
        "interview_orchestrator.shared.factories.company_factory.AgentProviderRegistry.get_agent_url"
    )
    def test_get_tools_custom_env_override(self, mock_get_agent_url):
        """Test that environment variable overrides work through registry."""
        # Simulate custom URL from environment variable
        mock_get_agent_url.return_value = "http://custom-env-agent:9999"

        tools = CompanyFactory.get_tools("google", "system_design")

        assert isinstance(tools, RemoteAgentProvider)
        assert tools.agent_url == "http://custom-env-agent:9999"
