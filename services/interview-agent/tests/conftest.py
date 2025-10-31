"""Shared test fixtures for interview-agent tests."""

import os
from unittest.mock import patch

import pytest

from interview_agent.shared.agent_providers.registry import AgentProviderRegistry


@pytest.fixture(autouse=True)
def mock_agent_env():
    """Mock environment variables for agent registry.

    This fixture automatically provides valid environment variables
    for all tests that use the AgentProviderRegistry.
    """
    env = {
        "INTERVIEW_AGENTS": "google,meta",
        "GOOGLE_AGENT_URL": "http://localhost:10123",
        "GOOGLE_AGENT_TYPES": "system_design,coding",
        "META_AGENT_URL": "http://localhost:10125",
        "META_AGENT_TYPES": "system_design",
    }

    # Reset registry cache before and after each test
    AgentProviderRegistry._DEFAULT_AGENTS = None

    with patch.dict(os.environ, env, clear=False):
        yield

    AgentProviderRegistry._DEFAULT_AGENTS = None
