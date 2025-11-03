"""Tests for AgentProviderRegistry."""

import os
from unittest.mock import patch

import pytest

from interview_agent.shared.agent_providers.registry import AgentProviderRegistry


@pytest.fixture(autouse=True)
def reset_registry():
    """Reset registry cache before and after each test."""
    AgentProviderRegistry._DEFAULT_AGENTS = None
    yield
    AgentProviderRegistry._DEFAULT_AGENTS = None


@pytest.fixture
def valid_env():
    """Fixture providing valid environment variables."""
    return {
        "INTERVIEW_AGENTS": "google,meta",
        "GOOGLE_AGENT_URL": "http://localhost:10123",
        "GOOGLE_AGENT_TYPES": "system_design,coding",
        "META_AGENT_URL": "http://localhost:10125",
        "META_AGENT_TYPES": "system_design",
    }


def test_load_agents_with_valid_env(valid_env):
    """Test loading agents with valid environment variables."""
    with patch.dict(os.environ, valid_env, clear=True):
        agents = AgentProviderRegistry._load_agents()

        assert "google" in agents
        assert "meta" in agents
        assert agents["google"].url == "http://localhost:10123"
        assert agents["google"].supported_types == ["system_design", "coding"]
        assert agents["meta"].url == "http://localhost:10125"
        assert agents["meta"].supported_types == ["system_design"]


def test_load_agents_missing_interview_agents():
    """Test that missing INTERVIEW_AGENTS returns empty dict (local-only mode)."""
    env = {
        "GOOGLE_AGENT_URL": "http://localhost:10123",
        "GOOGLE_AGENT_TYPES": "system_design,coding",
    }

    with patch.dict(os.environ, env, clear=True):
        agents = AgentProviderRegistry._load_agents()
        assert agents == {}  # Should return empty dict for local-only mode


def test_load_agents_missing_url():
    """Test that missing URL environment variable raises ValueError."""
    env = {
        "INTERVIEW_AGENTS": "google,meta",
        "GOOGLE_AGENT_TYPES": "system_design,coding",
        "META_AGENT_URL": "http://localhost:10125",
        "META_AGENT_TYPES": "system_design",
    }

    with patch.dict(os.environ, env, clear=True):
        expected_error = "Missing required environment variable: GOOGLE_AGENT_URL"
        with pytest.raises(ValueError, match=expected_error):
            AgentProviderRegistry._load_agents()


def test_load_agents_missing_types():
    """Test that missing TYPES environment variable raises ValueError."""
    env = {
        "INTERVIEW_AGENTS": "google,meta",
        "GOOGLE_AGENT_URL": "http://localhost:10123",
        "GOOGLE_AGENT_TYPES": "system_design,coding",
        "META_AGENT_URL": "http://localhost:10125",
    }

    with patch.dict(os.environ, env, clear=True):
        expected_error = "Missing required environment variable: META_AGENT_TYPES"
        with pytest.raises(ValueError, match=expected_error):
            AgentProviderRegistry._load_agents()


def test_get_available_options_returns_sorted_dict(valid_env):
    """Test get_available_options returns sorted dict mapping company to types."""
    env_unsorted = valid_env.copy()
    env_unsorted["GOOGLE_AGENT_TYPES"] = "coding,system_design"  # Reverse order

    with patch.dict(os.environ, env_unsorted, clear=True):
        options = AgentProviderRegistry.get_available_options()

        # Should return dict
        assert isinstance(options, dict)
        # Should be sorted by company
        assert list(options.keys()) == ["google", "meta"]
        # Types should be sorted
        assert options["google"] == ["coding", "system_design"]
        assert options["meta"] == ["system_design"]


def test_get_formatted_options(valid_env):
    """Test get_formatted_options returns formatted string."""
    with patch.dict(os.environ, valid_env, clear=True):
        formatted = AgentProviderRegistry.get_formatted_options()
        expected = "- Google coding\n- Google system_design\n- Meta system_design"
        assert formatted == expected


def test_is_valid_combination_valid(valid_env):
    """Test is_valid_combination returns True for valid combinations."""
    with patch.dict(os.environ, valid_env, clear=True):
        assert AgentProviderRegistry.is_valid_combination("google", "system_design")
        assert AgentProviderRegistry.is_valid_combination("google", "coding")
        assert AgentProviderRegistry.is_valid_combination("meta", "system_design")
        # Case insensitive
        assert AgentProviderRegistry.is_valid_combination("GOOGLE", "CODING")


def test_is_valid_combination_invalid(valid_env):
    """Test is_valid_combination returns False for invalid combinations."""
    with patch.dict(os.environ, valid_env, clear=True):
        # Invalid company
        assert not AgentProviderRegistry.is_valid_combination("amazon", "system_design")
        # Invalid type for company
        assert not AgentProviderRegistry.is_valid_combination("meta", "coding")


def test_get_agent_url_valid(valid_env):
    """Test get_agent_url returns URL for valid combination."""
    with patch.dict(os.environ, valid_env, clear=True):
        assert AgentProviderRegistry.get_agent_url("google", "coding") == "http://localhost:10123"
        assert (
            AgentProviderRegistry.get_agent_url("meta", "system_design") == "http://localhost:10125"
        )


def test_get_agent_url_invalid(valid_env):
    """Test get_agent_url returns None for invalid combination."""
    with patch.dict(os.environ, valid_env, clear=True):
        assert AgentProviderRegistry.get_agent_url("meta", "coding") is None
        assert AgentProviderRegistry.get_agent_url("amazon", "system_design") is None


def test_types_whitespace_handling():
    """Test that whitespace in types is handled correctly."""
    env = {
        "INTERVIEW_AGENTS": "google,meta",
        "GOOGLE_AGENT_URL": "http://localhost:10123",
        "GOOGLE_AGENT_TYPES": " system_design , coding , behavioral ",
        "META_AGENT_URL": "http://localhost:10125",
        "META_AGENT_TYPES": "system_design",
    }

    with patch.dict(os.environ, env, clear=True):
        options = AgentProviderRegistry.get_available_options()
        # Should strip whitespace and sort
        assert options["google"] == ["behavioral", "coding", "system_design"]
