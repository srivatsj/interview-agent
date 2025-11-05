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
    """Test get_available_options returns sorted dict mapping company to types.

    Now includes both remote agents (from env) and free default agents.
    """
    env_unsorted = valid_env.copy()
    env_unsorted["GOOGLE_AGENT_TYPES"] = "coding,system_design"  # Reverse order

    with patch.dict(os.environ, env_unsorted, clear=True):
        options = AgentProviderRegistry.get_available_options()

        # Should return dict
        assert isinstance(options, dict)
        # Should include remote agents (google, meta) AND free default agent
        assert "google" in options
        assert "meta" in options
        assert "default" in options  # Free default agent
        # Should be sorted by company (alphabetically)
        assert list(options.keys()) == ["default", "google", "meta"]
        # Types should be sorted
        assert options["google"] == ["coding", "system_design"]
        assert options["meta"] == ["system_design"]
        assert options["default"] == ["system_design"]


def test_get_formatted_options(valid_env):
    """Test get_formatted_options returns formatted string.

    Now includes both remote agents and free default agents.
    """
    with patch.dict(os.environ, valid_env, clear=True):
        formatted = AgentProviderRegistry.get_formatted_options()
        expected = (
            "- Default system_design\n- Google coding\n- Google system_design\n- Meta system_design"
        )
        assert formatted == expected


def test_is_valid_combination_valid(valid_env):
    """Test is_valid_combination returns True for valid combinations.

    Now includes both remote agents and free default agents.
    """
    with patch.dict(os.environ, valid_env, clear=True):
        # Remote agents
        assert AgentProviderRegistry.is_valid_combination("google", "system_design")
        assert AgentProviderRegistry.is_valid_combination("google", "coding")
        assert AgentProviderRegistry.is_valid_combination("meta", "system_design")
        # Free default agent
        assert AgentProviderRegistry.is_valid_combination("default", "system_design")
        # Case insensitive
        assert AgentProviderRegistry.is_valid_combination("GOOGLE", "CODING")
        assert AgentProviderRegistry.is_valid_combination("DEFAULT", "SYSTEM_DESIGN")


def test_is_valid_combination_invalid(valid_env):
    """Test is_valid_combination returns False for invalid combinations."""
    with patch.dict(os.environ, valid_env, clear=True):
        # Invalid company (not in remote or free default)
        assert not AgentProviderRegistry.is_valid_combination("acme", "system_design")
        assert not AgentProviderRegistry.is_valid_combination("amazon", "system_design")
        assert not AgentProviderRegistry.is_valid_combination("unknown_company", "system_design")
        # Invalid type for company
        assert not AgentProviderRegistry.is_valid_combination("meta", "coding")
        # default only has system_design
        assert not AgentProviderRegistry.is_valid_combination("default", "coding")


def test_get_agent_url_valid(valid_env):
    """Test get_agent_url returns URL for valid combination."""
    with patch.dict(os.environ, valid_env, clear=True):
        assert AgentProviderRegistry.get_agent_url("google", "coding") == "http://localhost:10123"
        assert (
            AgentProviderRegistry.get_agent_url("meta", "system_design") == "http://localhost:10125"
        )


def test_get_agent_url_invalid(valid_env):
    """Test get_agent_url returns None for invalid combination or free default agent.

    Note: Free default agent is a valid combination but returns None for URL
    since it uses local tools, not remote agent.
    """
    with patch.dict(os.environ, valid_env, clear=True):
        # Invalid type for company
        assert AgentProviderRegistry.get_agent_url("meta", "coding") is None
        # Free default agent returns None (no remote URL)
        assert AgentProviderRegistry.get_agent_url("default", "system_design") is None


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


def test_local_only_mode():
    """Test that local-only mode (no INTERVIEW_AGENTS) still provides free default agent."""
    # Don't set INTERVIEW_AGENTS - should use only free default agent
    with patch.dict(os.environ, {}, clear=True):
        options = AgentProviderRegistry.get_available_options()

        # Should only have free default agent
        assert options == {
            "default": ["system_design"],
        }

        # Validation should work for free default agent
        assert AgentProviderRegistry.is_valid_combination("default", "system_design")

        # No remote agent URLs should be available
        assert AgentProviderRegistry.get_agent_url("default", "system_design") is None

        # Formatted options should show free default agent
        formatted = AgentProviderRegistry.get_formatted_options()
        expected = "- Default system_design"
        assert formatted == expected
