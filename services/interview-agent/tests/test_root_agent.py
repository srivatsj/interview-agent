"""Unit tests for RootCustomAgent"""

from typing import ClassVar
from unittest.mock import AsyncMock, Mock, patch

import pytest
from google.adk.agents import BaseAgent
from google.adk.tools import ToolContext

from interview_agent.root_agent import RootCustomAgent


def create_mock_context(state=None):
    """Create a properly mocked InvocationContext for testing"""
    ctx = Mock()
    ctx.session = Mock()
    ctx.session.state = state if state is not None else {}

    # Mock plugin_manager for agents that use run_async internally
    plugin_manager = Mock()
    plugin_manager.run_before_agent_callback = AsyncMock(return_value=None)
    plugin_manager.run_after_agent_callback = AsyncMock(return_value=None)
    ctx.plugin_manager = plugin_manager

    # Mock model_copy for Pydantic context cloning
    ctx.model_copy = Mock(return_value=ctx)

    return ctx


class TestSetRoutingDecision:
    """Test set_routing_decision tool validation"""

    def test_invalid_company(self):
        """Test invalid company returns error"""
        ctx = Mock(spec=ToolContext)
        ctx.state = {}
        result = RootCustomAgent.set_routing_decision("invalid_company", "system_design", ctx)

        assert "Error: Invalid company" in result

    def test_invalid_interview_type(self):
        """Test invalid interview type returns error"""
        ctx = Mock(spec=ToolContext)
        ctx.state = {}
        result = RootCustomAgent.set_routing_decision("google", "invalid_type", ctx)

        assert "Error: Invalid interview type" in result

    def test_valid_routing(self):
        """Test valid routing saves to state"""
        ctx = Mock(spec=ToolContext)
        ctx.state = {}

        result = RootCustomAgent.set_routing_decision("google", "system_design", ctx)

        assert "Routing saved: google system_design" in result
        assert "routing_decision" in ctx.state
        assert ctx.state["routing_decision"]["company"] == "google"


class TestRootCustomAgentDelegation:
    """Test RootCustomAgent delegates to correct orchestrator"""

    @pytest.mark.asyncio
    async def test_delegates_to_system_design_orchestrator(self):
        """Test _run_async_impl delegates to system_design orchestrator - NO LLM CALLS"""

        # Create custom orchestrator that tracks calls
        class MockOrchestrator(BaseAgent):
            model_config = {"arbitrary_types_allowed": True}
            called: ClassVar[bool] = False

            def __init__(self, **kwargs):
                super().__init__(name="mock_orchestrator", description="Mock")

            async def run_async(self, _ctx):
                MockOrchestrator.called = True
                # Empty async generator
                if False:
                    yield

        # Mock SystemDesignOrchestrator to return our mock
        with (
            patch("interview_agent.root_agent.SystemDesignOrchestrator", MockOrchestrator),
            patch("interview_agent.root_agent.SystemDesignAgent"),
        ):
            agent = RootCustomAgent()

            # Create context with system_design routing pre-set (no LLM call needed)
            ctx = create_mock_context(
                {"routing_decision": {"company": "amazon", "interview_type": "system_design"}}
            )

            # Execute _run_async_impl directly
            async for _ in agent._run_async_impl(ctx):
                pass

            # Verify orchestrator was invoked
            assert MockOrchestrator.called, "Orchestrator should have been called"

    @pytest.mark.asyncio
    async def test_run_async_coding_logs_warning(self, caplog):
        """Test coding interview logs warning - NO LLM CALLS"""
        agent = RootCustomAgent()

        # Pre-set coding routing (no LLM call)
        ctx = create_mock_context(
            {"routing_decision": {"company": "google", "interview_type": "coding"}}
        )

        # Run agent
        async for _ in agent._run_async_impl(ctx):
            pass

        # Check for warning log
        assert any("Coding interviews not yet implemented" in rec.message for rec in caplog.records)

    @pytest.mark.asyncio
    async def test_run_async_behavioral_logs_warning(self, caplog):
        """Test behavioral interview logs warning - NO LLM CALLS"""
        agent = RootCustomAgent()

        # Pre-set behavioral routing (no LLM call)
        ctx = create_mock_context(
            {"routing_decision": {"company": "apple", "interview_type": "behavioral"}}
        )

        # Run agent
        async for _ in agent._run_async_impl(ctx):
            pass

        # Check for warning log
        assert any(
            "Behavioral interviews not yet implemented" in rec.message for rec in caplog.records
        )
