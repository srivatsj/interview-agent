"""Tests for SystemDesignAgent"""

from unittest.mock import AsyncMock, Mock

import pytest

from interview_agent.interview_types.system_design.company_factory import CompanyFactory
from interview_agent.interview_types.system_design.system_design_agent import (
    SystemDesignAgent,
)


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


class TestSystemDesignAgentInitialization:
    """Test SystemDesignAgent initialization"""

    def test_initialization_with_amazon_tools(self):
        """Test initialization with Amazon tools"""
        tools = CompanyFactory.get_tools("test_company", "system_design")
        agent = SystemDesignAgent(tool_provider=tools, name="amazon_system_design_orchestrator")

        assert agent.name == "amazon_system_design_orchestrator"
        assert agent.phases is not None
        assert len(agent.phases) == 6
        assert agent.phase_agent is not None

    def test_initialization_with_default_name(self):
        """Test initialization with default name"""
        tools = CompanyFactory.get_tools("test_company", "system_design")
        agent = SystemDesignAgent(tool_provider=tools)

        assert agent.name == "system_design_orchestrator"
        assert agent.phases is not None
        assert agent.phase_agent is not None

    def test_phases_loaded(self):
        """Test phases are loaded during initialization"""
        tools = CompanyFactory.get_tools("test_company", "system_design")
        agent = SystemDesignAgent(tool_provider=tools)

        # Verify all 6 phases loaded (including get_problem)
        assert len(agent.phases) == 6
        assert agent.phases[0]["id"] == "get_problem"
        assert agent.phases[1]["id"] == "problem_clarification"
        assert agent.phases[-1]["id"] == "hld"


class TestSystemDesignAgentOrchestration:
    """Test SystemDesignAgent phase orchestration"""

    @pytest.mark.asyncio
    async def test_starts_first_phase(self):
        """Test orchestrator starts with first phase when phase_idx=0"""
        tools = CompanyFactory.get_tools("test_company", "system_design")
        agent = SystemDesignAgent(tool_provider=tools)

        # Start with phase 0
        ctx = create_mock_context({"current_phase_idx": 0})

        events = []
        async for event in agent._run_async_impl(ctx):
            events.append(event)

        # Verify phase state was set via events (not direct state modification)
        # First event should set phase state
        assert len(events) >= 1
        first_event = events[0]
        assert first_event.actions.state_delta["current_phase"] == "get_problem"
        assert first_event.actions.state_delta["current_phase_idx"] == 0
        assert first_event.actions.state_delta["phase_complete"] is False

    @pytest.mark.asyncio
    async def test_transitions_to_next_phase(self):
        """Test orchestrator transitions to next phase"""
        tools = CompanyFactory.get_tools("test_company", "system_design")
        agent = SystemDesignAgent(tool_provider=tools)

        ctx = create_mock_context({"current_phase_idx": 0})

        events = []
        async for event in agent._run_async_impl(ctx):
            events.append(event)

        # Verify transition event sets next phase index
        assert any(
            hasattr(e, "actions")
            and e.actions
            and e.actions.state_delta
            and e.actions.state_delta.get("current_phase_idx") == 1
            for e in events
        ), "Should transition to phase index 1"

    @pytest.mark.asyncio
    async def test_completes_when_all_phases_done(self):
        """Test orchestrator completes when phase_idx >= num_phases"""
        tools = CompanyFactory.get_tools("test_company", "system_design")
        agent = SystemDesignAgent(tool_provider=tools)

        # Set phase index beyond last phase (6 phases total, so idx 6 is complete)
        ctx = create_mock_context({"current_phase_idx": 6})

        events = []
        async for event in agent._run_async_impl(ctx):
            events.append(event)

        # Verify completion event yielded
        assert len(events) == 1, "Should yield exactly one completion event"
        assert events[0].author == agent.name
        assert events[0].actions.state_delta.get("interview_phases_complete") is True

    @pytest.mark.asyncio
    async def test_runs_middle_phase(self):
        """Test orchestrator can run middle phases"""
        tools = CompanyFactory.get_tools("test_company", "system_design")
        agent = SystemDesignAgent(tool_provider=tools)

        # Start at middle phase (requirements is now index 2)
        ctx = create_mock_context({"current_phase_idx": 2})

        events = []
        async for event in agent._run_async_impl(ctx):
            events.append(event)

        # Verify correct phase was set via events
        assert len(events) >= 1
        first_event = events[0]
        assert first_event.actions.state_delta["current_phase"] == "requirements"


class TestSystemDesignAgentStateManagement:
    """Test SystemDesignAgent state management"""

    @pytest.mark.asyncio
    async def test_resets_phase_state_each_iteration(self):
        """Test orchestrator resets phase state for each phase"""
        tools = CompanyFactory.get_tools("test_company", "system_design")
        agent = SystemDesignAgent(tool_provider=tools)

        ctx = create_mock_context(
            {
                "current_phase_idx": 1,
                "phase_complete": True,  # From previous phase
            }
        )

        events = []
        async for event in agent._run_async_impl(ctx):
            events.append(event)

        # Verify state was reset for new phase via events
        assert len(events) >= 1
        first_event = events[0]
        # New architecture resets phase_complete to False
        assert first_event.actions.state_delta["phase_complete"] is False
        assert first_event.actions.state_delta["current_phase"] == "problem_clarification"
