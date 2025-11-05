"""Tests for SystemDesignAgent"""

from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio

from interview_agent.interview_types.system_design.system_design_agent import (
    SystemDesignAgent,
)
from interview_agent.shared.factories import CompanyFactory


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


@pytest_asyncio.fixture
async def default_phases():
    """Fixture providing default test phases"""
    tools = CompanyFactory.get_tools("test_company", "system_design")
    return await tools.get_phases()


class TestSystemDesignAgentInitialization:
    """Test SystemDesignAgent initialization"""

    def test_initialization_with_amazon_tools(self, default_phases):
        """Test initialization with Amazon tools"""
        tools = CompanyFactory.get_tools("test_company", "system_design")
        agent = SystemDesignAgent(
            tool_provider=tools, phases=default_phases, name="amazon_system_design_orchestrator"
        )

        assert agent.name == "amazon_system_design_orchestrator"
        assert agent.phases is not None
        assert len(agent.phases) == 5
        assert agent.phase_agent is not None

    def test_initialization_with_default_name(self, default_phases):
        """Test initialization with default name"""
        tools = CompanyFactory.get_tools("test_company", "system_design")
        agent = SystemDesignAgent(tool_provider=tools, phases=default_phases)

        assert agent.name == "system_design_orchestrator"
        assert agent.phases is not None
        assert agent.phase_agent is not None

    def test_phases_loaded(self, default_phases):
        """Test phases are loaded during initialization"""
        tools = CompanyFactory.get_tools("test_company", "system_design")
        agent = SystemDesignAgent(tool_provider=tools, phases=default_phases)

        # Verify all 5 phases loaded
        assert len(agent.phases) == 5
        assert agent.phases[0]["id"] == "problem_clarification"
        assert agent.phases[1]["id"] == "requirements"
        assert agent.phases[-1]["id"] == "hld"


class TestSystemDesignAgentOrchestration:
    """Test SystemDesignAgent phase orchestration"""

    @pytest.mark.asyncio
    async def test_starts_first_phase(self, default_phases):
        """Test orchestrator starts with first phase when phase_idx=0"""
        tools = CompanyFactory.get_tools("test_company", "system_design")
        agent = SystemDesignAgent(tool_provider=tools, phases=default_phases)

        # Start with phase 0
        ctx = create_mock_context({"current_phase_idx": 0})

        events = []
        async for event in agent._run_async_impl(ctx):
            events.append(event)

        # Verify phase state was set via events (not direct state modification)
        # First event should set interview_question, second event should set phase state
        assert len(events) >= 2
        # First event sets the question
        question_event = events[0]
        assert "interview_question" in question_event.actions.state_delta
        # Second event sets the phase
        phase_event = events[1]
        assert phase_event.actions.state_delta["current_phase"] == "problem_clarification"
        assert phase_event.actions.state_delta["current_phase_idx"] == 0
        assert phase_event.actions.state_delta["phase_complete"] is False

    @pytest.mark.asyncio
    async def test_transitions_to_next_phase(self, default_phases):
        """Test orchestrator transitions to next phase"""
        tools = CompanyFactory.get_tools("test_company", "system_design")
        agent = SystemDesignAgent(tool_provider=tools, phases=default_phases)

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
    async def test_completes_when_all_phases_done(self, default_phases):
        """Test orchestrator completes when phase_idx >= num_phases"""
        tools = CompanyFactory.get_tools("test_company", "system_design")
        agent = SystemDesignAgent(tool_provider=tools, phases=default_phases)

        # Set phase index beyond last phase (5 phases total, so idx 5 is complete)
        ctx = create_mock_context({"current_phase_idx": 5})

        events = []
        async for event in agent._run_async_impl(ctx):
            events.append(event)

        # Verify completion event yielded
        assert len(events) == 1, "Should yield exactly one completion event"
        assert events[0].author == agent.name
        assert events[0].actions.state_delta.get("interview_phases_complete") is True

    @pytest.mark.asyncio
    async def test_runs_middle_phase(self, default_phases):
        """Test orchestrator can run middle phases"""
        tools = CompanyFactory.get_tools("test_company", "system_design")
        agent = SystemDesignAgent(tool_provider=tools, phases=default_phases)

        # Start at middle phase (data_design is index 2)
        ctx = create_mock_context({"current_phase_idx": 2})

        events = []
        async for event in agent._run_async_impl(ctx):
            events.append(event)

        # Verify correct phase was set via events
        assert len(events) >= 1
        first_event = events[0]
        assert first_event.actions.state_delta["current_phase"] == "data_design"


class TestSystemDesignAgentStateManagement:
    """Test SystemDesignAgent state management"""

    @pytest.mark.asyncio
    async def test_resets_phase_state_each_iteration(self, default_phases):
        """Test orchestrator resets phase state for each phase"""
        tools = CompanyFactory.get_tools("test_company", "system_design")
        agent = SystemDesignAgent(tool_provider=tools, phases=default_phases)

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
        # Phase idx 1 = requirements (0=problem_clarification, 1=requirements, ...)
        assert first_event.actions.state_delta["current_phase"] == "requirements"


class TestSystemDesignAgentQuestionFetching:
    """Test SystemDesignAgent question fetching"""

    @pytest.mark.asyncio
    async def test_fetches_question_at_start(self, default_phases):
        """Test orchestrator fetches question at phase 0 start"""
        tools = CompanyFactory.get_tools("test_company", "system_design")
        agent = SystemDesignAgent(tool_provider=tools, phases=default_phases)

        # Start with phase 0, no question in state
        ctx = create_mock_context({"current_phase_idx": 0})

        events = []
        async for event in agent._run_async_impl(ctx):
            events.append(event)

        # First event should set the interview_question
        assert len(events) >= 2
        question_event = events[0]
        assert "interview_question" in question_event.actions.state_delta
        assert isinstance(question_event.actions.state_delta["interview_question"], str)
        assert len(question_event.actions.state_delta["interview_question"]) > 0

    @pytest.mark.asyncio
    async def test_does_not_refetch_question_if_exists(self, default_phases):
        """Test orchestrator does not refetch question if already in state"""
        tools = CompanyFactory.get_tools("test_company", "system_design")
        agent = SystemDesignAgent(tool_provider=tools, phases=default_phases)

        # Start with question already in state
        existing_question = "Design a URL shortener"
        ctx = create_mock_context({"current_phase_idx": 0, "interview_question": existing_question})

        events = []
        async for event in agent._run_async_impl(ctx):
            events.append(event)

        # Should NOT set interview_question again
        for event in events:
            if hasattr(event, "actions") and event.actions and event.actions.state_delta:
                assert "interview_question" not in event.actions.state_delta

    @pytest.mark.asyncio
    async def test_does_not_fetch_question_after_phase_0(self, default_phases):
        """Test orchestrator does not fetch question after phase 0"""
        tools = CompanyFactory.get_tools("test_company", "system_design")
        agent = SystemDesignAgent(tool_provider=tools, phases=default_phases)

        # Start at phase 1, no question in state
        ctx = create_mock_context({"current_phase_idx": 1})

        events = []
        async for event in agent._run_async_impl(ctx):
            events.append(event)

        # Should NOT fetch question (only fetches at phase 0)
        for event in events:
            if hasattr(event, "actions") and event.actions and event.actions.state_delta:
                assert "interview_question" not in event.actions.state_delta
