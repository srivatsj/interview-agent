"""Tests for PhaseAgent with LoopAgent pattern"""

from unittest.mock import Mock, patch

import pytest
from google.adk.sessions import Session

from interview_agent.interview_types.system_design.providers import (
    AmazonSystemDesignTools,
)
from interview_agent.interview_types.system_design.sub_agents import PhaseAgent


class TestPhaseAgent:
    """Test PhaseAgent initialization and configuration"""

    def test_initialization_with_tools(self):
        """Test PhaseAgent initializes correctly"""
        tools = AmazonSystemDesignTools()
        agent = PhaseAgent(tools)

        assert agent.name == "phase_agent"
        assert agent.tool_provider == tools
        assert agent.max_turns == 10  # Default value

    def test_initialization_with_custom_max_turns(self):
        """Test PhaseAgent accepts custom max_turns"""
        tools = AmazonSystemDesignTools()
        agent = PhaseAgent(tools, max_turns=5)

        assert agent.max_turns == 5

    def test_get_phase_instruction(self):
        """Test phase instruction generation"""
        tools = AmazonSystemDesignTools()
        agent = PhaseAgent(tools)

        instruction = agent._get_phase_instruction("data_design")

        assert "data_design" in instruction.lower()
        assert "database" in instruction.lower()
        assert "schema" in instruction.lower()

    def test_get_phase_instruction_for_different_phases(self):
        """Test instruction varies by phase"""
        tools = AmazonSystemDesignTools()
        agent = PhaseAgent(tools)

        inst1 = agent._get_phase_instruction("data_design")
        inst2 = agent._get_phase_instruction("problem_clarification")

        assert inst1 != inst2
        assert "data" in inst1.lower()
        assert "problem" in inst2.lower()

    @pytest.mark.asyncio
    async def test_run_creates_loop_agent(self):
        """Test PhaseAgent creates and runs LoopAgent"""
        tools = AmazonSystemDesignTools()
        agent = PhaseAgent(tools, max_turns=3)

        class MockContext:
            session = Session(
                id="test",
                app_name="test",
                user_id="test",
                state={"current_phase": "data_design"},
                events=[],
            )

        ctx = MockContext()

        # Mock LoopAgent to prevent actual execution
        with patch(
            "interview_agent.interview_types.system_design.sub_agents.phase_agent.LoopAgent"
        ) as MockLoopAgent:
            # Create an async generator that yields nothing
            async def mock_async_gen():
                return
                yield  # Make it a generator

            mock_loop_instance = Mock()
            mock_loop_instance.run_async = Mock(return_value=mock_async_gen())
            MockLoopAgent.return_value = mock_loop_instance

            events = []
            async for event in agent._run_async_impl(ctx):
                events.append(event)

            # Verify LoopAgent was created with correct params
            MockLoopAgent.assert_called_once()
            call_kwargs = MockLoopAgent.call_args.kwargs

            assert call_kwargs["name"] == "phase_data_design_loop"
            assert call_kwargs["max_iterations"] == 3
            assert len(call_kwargs["sub_agents"]) == 2

    @pytest.mark.asyncio
    async def test_run_resets_turn_count(self):
        """Test PhaseAgent resets turn count at start"""
        tools = AmazonSystemDesignTools()
        agent = PhaseAgent(tools)

        class MockContext:
            session = Session(
                id="test",
                app_name="test",
                user_id="test",
                state={"current_phase": "data_design", "phase_turn_count": 5},
                events=[],
            )

        ctx = MockContext()

        with patch(
            "interview_agent.interview_types.system_design.sub_agents.phase_agent.LoopAgent"
        ) as MockLoopAgent:
            # Create an async generator that yields nothing
            async def mock_async_gen():
                return
                yield  # Make it a generator

            mock_loop_instance = Mock()
            mock_loop_instance.run_async = Mock(return_value=mock_async_gen())
            MockLoopAgent.return_value = mock_loop_instance

            async for _ in agent._run_async_impl(ctx):
                pass

            assert ctx.session.state["phase_turn_count"] == 0


class TestPhaseAgentIntegration:
    """Integration tests with real tool provider"""

    def test_all_phases_have_valid_instructions(self):
        """Test instruction generation works for all phases"""
        tools = AmazonSystemDesignTools()
        agent = PhaseAgent(tools)
        phases = tools.get_phases()

        for phase in phases:
            instruction = agent._get_phase_instruction(phase["id"])
            assert len(instruction) > 0
            assert phase["id"] in instruction.lower()
