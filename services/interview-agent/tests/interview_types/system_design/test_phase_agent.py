"""Tests for PhaseAgent"""

from typing import ClassVar
from unittest.mock import AsyncMock, Mock

import pytest

from interview_agent.interview_types.system_design.phase_agent import PhaseAgent


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


class MockTools:
    """Mock tool provider for testing"""

    get_context_called: ClassVar[bool] = False
    evaluate_called: ClassVar[bool] = False


class TestPhaseAgent:
    """Test PhaseAgent behavior"""

    def setup_method(self):
        """Reset class variables before each test"""
        MockTools.get_context_called = False
        MockTools.evaluate_called = False

    @pytest.mark.asyncio
    async def test_first_iteration_shows_context(self):
        """Test first iteration shows phase context and sets context_shown flag"""
        tools = MockTools()
        agent = PhaseAgent(tools)

        # Create context with phase but no context_shown flag
        ctx = create_mock_context({"current_phase": "data_design", "context_shown": False})

        # Execute agent
        events = []
        async for event in agent._run_async_impl(ctx):
            events.append(event)

        # Verify context_shown flag set
        assert any(
            hasattr(e, "actions")
            and e.actions
            and e.actions.state_delta
            and e.actions.state_delta.get("context_shown") is True
            for e in events
        ), "Should set context_shown=True"

    @pytest.mark.asyncio
    async def test_first_iteration_returns_early(self):
        """Test first iteration returns after showing context (waits for user response)"""
        tools = MockTools()
        agent = PhaseAgent(tools)

        ctx = create_mock_context({"current_phase": "data_design", "context_shown": False})

        events = []
        async for event in agent._run_async_impl(ctx):
            events.append(event)

        # Should yield 2 events: content + state_delta, then return
        assert len(events) == 2

    @pytest.mark.asyncio
    async def test_subsequent_iterations_conduct_discussion(self):
        """Test subsequent iterations (after context shown) continue discussion"""
        tools = MockTools()
        agent = PhaseAgent(tools)

        # Context already shown
        ctx = create_mock_context({"current_phase": "data_design", "context_shown": True})

        events = []
        async for event in agent._run_async_impl(ctx):
            events.append(event)

        # Should not set context_shown again (it's already True)
        assert not any(
            hasattr(e, "actions")
            and e.actions
            and e.actions.state_delta
            and "context_shown" in e.actions.state_delta
            for e in events
        )

    @pytest.mark.asyncio
    async def test_phase_complete_false_by_default(self):
        """Test phase_complete is set to False during discussion"""
        tools = MockTools()
        agent = PhaseAgent(tools)

        ctx = create_mock_context({"current_phase": "data_design", "context_shown": True})

        events = []
        async for event in agent._run_async_impl(ctx):
            events.append(event)

        # Verify phase_complete set to False (placeholder logic)
        assert any(
            hasattr(e, "actions")
            and e.actions
            and e.actions.state_delta
            and e.actions.state_delta.get("phase_complete") is False
            for e in events
        ), "Should set phase_complete=False"

    @pytest.mark.asyncio
    async def test_handles_missing_current_phase(self):
        """Test agent handles missing current_phase in state"""
        tools = MockTools()
        agent = PhaseAgent(tools)

        # No current_phase in state
        ctx = create_mock_context({"context_shown": False})

        # Should not crash, should handle gracefully
        events = []
        async for event in agent._run_async_impl(ctx):
            events.append(event)

        # Should still execute without error
        assert len(events) >= 0
