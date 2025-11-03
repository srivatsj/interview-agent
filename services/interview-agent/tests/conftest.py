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
    # Load API key from .env or use environment
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        # If not in environment, try loading from .env
        from dotenv import load_dotenv

        load_dotenv()
        api_key = os.getenv("GOOGLE_API_KEY")

    env = {
        "INTERVIEW_AGENTS": "google,meta",
        "GOOGLE_AGENT_URL": "http://localhost:10123",
        "GOOGLE_AGENT_TYPES": "system_design,coding",
        "META_AGENT_URL": "http://localhost:10125",
        "META_AGENT_TYPES": "system_design",
        "GOOGLE_GENAI_USE_VERTEXAI": "FALSE",  # Use Google AI Studio, not Vertex AI
    }

    # Add API key if we found it
    if api_key:
        env["GOOGLE_API_KEY"] = api_key

    # Reset registry cache before and after each test
    AgentProviderRegistry._DEFAULT_AGENTS = None

    with patch.dict(os.environ, env, clear=False):
        yield

    AgentProviderRegistry._DEFAULT_AGENTS = None
