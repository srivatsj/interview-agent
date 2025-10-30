"""Tests for AgentProviderRegistry using environment variable mocking."""

import os
from unittest.mock import patch

from interview_agent.shared.agent_providers import AgentProviderRegistry


def test_get_agent_url_default_google():
    """Test retrieving default Google agent URL."""
    url = AgentProviderRegistry.get_agent_url("google", "system_design")
    assert url == "http://localhost:10123"


def test_get_agent_url_default_meta():
    """Test retrieving default Meta agent URL."""
    url = AgentProviderRegistry.get_agent_url("meta", "system_design")
    assert url == "http://localhost:10125"


def test_get_agent_url_case_insensitive():
    """Test that company name is case insensitive."""
    url_upper = AgentProviderRegistry.get_agent_url("GOOGLE", "system_design")
    url_lower = AgentProviderRegistry.get_agent_url("google", "system_design")
    url_mixed = AgentProviderRegistry.get_agent_url("Google", "system_design")

    assert url_upper == "http://localhost:10123"
    assert url_lower == "http://localhost:10123"
    assert url_mixed == "http://localhost:10123"


def test_get_agent_url_missing_agent():
    """Test that None is returned for missing agent."""
    url = AgentProviderRegistry.get_agent_url("unknown_company", "system_design")
    assert url is None


def test_get_agent_url_wrong_interview_type():
    """Test that None is returned for wrong interview type."""
    url = AgentProviderRegistry.get_agent_url("google", "behavioral")
    assert url is None


@patch.dict(os.environ, {"GOOGLE_SYSTEM_DESIGN_AGENT_URL": "http://custom:8000"})
def test_get_agent_url_env_override():
    """Test environment variable override for Google agent."""
    url = AgentProviderRegistry.get_agent_url("google", "system_design")
    assert url == "http://custom:8000"


@patch.dict(os.environ, {"META_SYSTEM_DESIGN_AGENT_URL": "http://custom-meta:9000"})
def test_get_agent_url_env_override_meta():
    """Test environment variable override for Meta agent."""
    url = AgentProviderRegistry.get_agent_url("meta", "system_design")
    assert url == "http://custom-meta:9000"


@patch.dict(
    os.environ,
    {
        "GOOGLE_SYSTEM_DESIGN_AGENT_URL": "http://google-override:8000",
        "META_SYSTEM_DESIGN_AGENT_URL": "http://meta-override:9000",
    },
)
def test_get_agent_url_multiple_env_overrides():
    """Test multiple environment variable overrides simultaneously."""
    google_url = AgentProviderRegistry.get_agent_url("google", "system_design")
    meta_url = AgentProviderRegistry.get_agent_url("meta", "system_design")

    assert google_url == "http://google-override:8000"
    assert meta_url == "http://meta-override:9000"


def test_list_available_agents():
    """Test listing all available agents."""
    agents = AgentProviderRegistry.list_available_agents()

    assert "google" in agents
    assert "meta" in agents
    assert agents["google"].url == "http://localhost:10123"
    assert agents["google"].interview_type == "system_design"
    assert agents["meta"].url == "http://localhost:10125"
    assert agents["meta"].interview_type == "system_design"
