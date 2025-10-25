"""Tests for SystemDesignAgent"""

from unittest.mock import AsyncMock, Mock

import pytest

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

    def test_valid_company_amazon(self):
        """Test initialization with valid company 'amazon'"""
        agent = SystemDesignAgent(company="amazon")

        assert agent.name == "amazon_system_design_orchestrator"
        assert agent.phases is not None
        assert len(agent.phases) > 0
        assert agent.phase_agent is not None

    def test_valid_company_google(self):
        """Test initialization with valid company 'google'"""
        # Google tools not yet implemented
        with pytest.raises(NotImplementedError, match="Tools for google not yet implemented"):
            SystemDesignAgent(company="google")

    def test_invalid_company_raises_error(self):
        """Test initialization with invalid company raises ValueError"""
        with pytest.raises(ValueError, match="Unknown company: invalid"):
            SystemDesignAgent(company="invalid")

    def test_phases_loaded(self):
        """Test phases are loaded during initialization"""
        agent = SystemDesignAgent(company="amazon")

        # Verify placeholder phases
        assert len(agent.phases) == 5
        assert agent.phases[0]["id"] == "problem_clarification"
        assert agent.phases[-1]["id"] == "hld"


class TestSystemDesignAgentOrchestration:
    """Test SystemDesignAgent phase orchestration"""

    @pytest.mark.asyncio
    async def test_starts_first_phase(self):
        """Test orchestrator starts with first phase when phase_idx=0"""
        agent = SystemDesignAgent(company="amazon")

        # Start with phase 0
        ctx = create_mock_context({"current_phase_idx": 0})

        events = []
        async for event in agent._run_async_impl(ctx):
            events.append(event)

        # Verify phase state was set
        assert ctx.session.state["current_phase"] == "problem_clarification"
        assert ctx.session.state["phase_complete"] is False
        assert ctx.session.state["context_shown"] is False

    @pytest.mark.asyncio
    async def test_transitions_to_next_phase(self):
        """Test orchestrator transitions to next phase"""
        agent = SystemDesignAgent(company="amazon")

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
        agent = SystemDesignAgent(company="amazon")

        # Set phase index beyond last phase
        ctx = create_mock_context({"current_phase_idx": 5})

        events = []
        async for event in agent._run_async_impl(ctx):
            events.append(event)

        # Verify completion event yielded
        assert len(events) == 1, "Should yield exactly one completion event"
        assert events[0].author == agent.name

    @pytest.mark.asyncio
    async def test_runs_middle_phase(self):
        """Test orchestrator can run middle phases"""
        agent = SystemDesignAgent(company="amazon")

        # Start at middle phase (data_design)
        ctx = create_mock_context({"current_phase_idx": 2})

        events = []
        async for event in agent._run_async_impl(ctx):
            events.append(event)

        # Verify correct phase was set
        assert ctx.session.state["current_phase"] == "data_design"


class TestSystemDesignAgentStateManagement:
    """Test SystemDesignAgent state management"""

    @pytest.mark.asyncio
    async def test_resets_phase_state_each_iteration(self):
        """Test orchestrator resets phase state for each phase"""
        agent = SystemDesignAgent(company="amazon")

        ctx = create_mock_context(
            {
                "current_phase_idx": 1,
                "phase_complete": True,  # From previous phase
                "context_shown": True,  # From previous phase
            }
        )

        events = []
        async for event in agent._run_async_impl(ctx):
            events.append(event)

        # Verify state was reset for new phase
        assert ctx.session.state["phase_complete"] is False
        assert ctx.session.state["context_shown"] is False
        assert ctx.session.state["current_phase"] == "requirements"
