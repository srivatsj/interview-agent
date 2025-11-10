"""
Unit tests for WebSocket server functionality.

Tests the server initialization and app creation without starting actual server.
"""

import pytest
from google.adk.agents import Agent
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.apps import App

from interview_orchestrator.server import create_app, create_run_config


class TestServerSetup:
    """Test server and app creation."""

    def test_create_app(self):
        """Test that create_app returns a valid ADK App."""
        app = create_app()

        assert isinstance(app, App)
        assert app.name == "interview_orchestrator"
        assert isinstance(app.root_agent, Agent)

    def test_create_app_has_root_agent(self):
        """Test that the app has a properly configured root agent."""
        app = create_app()

        assert app.root_agent.name == "interview_agent"
        assert callable(app.root_agent.instruction)  # Dynamic instruction

    def test_create_run_config(self):
        """Test that create_run_config returns proper BIDI config."""
        config = create_run_config()

        assert isinstance(config, RunConfig)
        assert config.streaming_mode == StreamingMode.BIDI

    def test_multiple_app_instances(self):
        """Test that multiple app instances can be created independently."""
        app1 = create_app()
        app2 = create_app()

        assert app1 is not app2
        # root_agent is shared (module-level), but apps are different
        assert app1.name == app2.name


class TestWebSocketIntegration:
    """
    Integration tests for WebSocket functionality.

    Note: These tests verify the setup without starting an actual server.
    For full E2E WebSocket tests, use a test client or manual testing.
    """

    @pytest.mark.asyncio
    async def test_app_can_be_instantiated(self):
        """Test that app can be created in async context."""
        app = create_app()
        assert app is not None

    def test_app_has_required_attributes(self):
        """Test that app has all required attributes for WebSocket server."""
        app = create_app()

        # Verify app structure
        assert hasattr(app, "name")
        assert hasattr(app, "root_agent")
        assert hasattr(app, "plugins")

        # Verify root agent is LlmAgent
        assert hasattr(app.root_agent, "run_async")
        assert callable(app.root_agent.run_async)
