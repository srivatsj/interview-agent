"""Tests for PhaseAgent with interactive evaluation"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from google.adk.events import Event
from google.adk.sessions import Session
from google.genai.types import Content, Part

from interview_orchestrator.interview_types.system_design.sub_agents import PhaseAgent
from interview_orchestrator.interview_types.system_design.tools import DefaultSystemDesignTools


class TestPhaseAgent:
    """Test PhaseAgent initialization and configuration"""

    def test_initialization_with_tools(self):
        """Test PhaseAgent initializes correctly"""
        tools = DefaultSystemDesignTools()
        agent = PhaseAgent(tools)

        assert agent.name == "phase_agent"
        assert agent.tool_provider == tools
        assert agent.max_turns == 10  # Default value

    def test_initialization_with_custom_max_turns(self):
        """Test PhaseAgent accepts custom max_turns"""
        tools = DefaultSystemDesignTools()
        agent = PhaseAgent(tools, max_turns=5)

        assert agent.max_turns == 5

    @pytest.mark.asyncio
    async def test_get_phase_instruction(self):
        """Test phase instruction generation"""
        tools = DefaultSystemDesignTools()
        agent = PhaseAgent(tools)

        class MockContext:
            session = Session(
                id="test",
                app_name="test",
                user_id="test",
                state={"interview_question": "Design a URL shortener"},
                events=[],
            )

        ctx = MockContext()
        instruction = await agent._get_phase_instruction(ctx, "data_design")

        assert "data_design" in instruction.lower()
        assert "database" in instruction.lower()
        assert "URL shortener" in instruction

    @pytest.mark.asyncio
    async def test_get_phase_instruction_for_different_phases(self):
        """Test instruction varies by phase"""
        tools = DefaultSystemDesignTools()
        agent = PhaseAgent(tools)

        class MockContext:
            session = Session(
                id="test",
                app_name="test",
                user_id="test",
                state={"interview_question": "Design a cache"},
                events=[],
            )

        ctx = MockContext()
        inst1 = await agent._get_phase_instruction(ctx, "data_design")
        inst2 = await agent._get_phase_instruction(ctx, "problem_clarification")

        assert inst1 != inst2
        assert "data" in inst1.lower()
        assert "problem" in inst2.lower()

    @pytest.mark.asyncio
    async def test_first_turn_llm_introduces_phase(self):
        """Test first turn (turn_count=0): LLM introduces phase"""
        tools = DefaultSystemDesignTools()
        agent = PhaseAgent(tools, max_turns=3)

        class MockContext:
            session = Session(
                id="test",
                app_name="test",
                user_id="test",
                state={"current_phase": "data_design", "phase_turn_count": 0},
                events=[],
            )

        ctx = MockContext()

        # Mock conversation agent
        with patch(
            "interview_orchestrator.interview_types.system_design.sub_agents.phase_agent.Agent"
        ) as MockAgent:

            async def mock_agent_run():
                yield Event(
                    author="phase_data_design_conversation",
                    content=Content(parts=[Part(text="Let's design the data model")]),
                )

            mock_agent_instance = Mock()
            mock_agent_instance.run_async = Mock(return_value=mock_agent_run())
            MockAgent.return_value = mock_agent_instance

            events = []
            async for event in agent._run_async_impl(ctx):
                events.append(event)

            # Should yield LLM response + turn count update
            assert len(events) == 2
            assert events[0].content.parts[0].text == "Let's design the data model"
            assert events[1].actions.state_delta["phase_turn_count"] == 1

    @pytest.mark.asyncio
    async def test_subsequent_turn_evaluates_and_continues(self):
        """Test subsequent turn with 'continue' decision: evaluates and asks follow-up"""
        tools = Mock()
        tools.evaluate_phase = AsyncMock(
            return_value={
                "decision": "continue",
                "score": 0.5,
                "gaps": ["Missing scaling details"],
                "followup_questions": "How will you handle scaling?",
            }
        )
        tools.get_context = AsyncMock(return_value="Data design context")

        agent = PhaseAgent(tools, max_turns=5)

        class MockContext:
            session = Session(
                id="test",
                app_name="test",
                user_id="test",
                state={
                    "current_phase": "data_design",
                    "phase_turn_count": 1,
                    "interview_question": "Design a cache",
                },
                events=[],
            )

        ctx = MockContext()

        # Mock conversation agent
        with patch(
            "interview_orchestrator.interview_types.system_design.sub_agents.phase_agent.Agent"
        ) as MockAgent:

            async def mock_agent_run():
                yield Event(
                    author="phase_data_design_conversation",
                    content=Content(parts=[Part(text="How will you handle scaling?")]),
                )

            mock_agent_instance = Mock()
            mock_agent_instance.run_async = Mock(return_value=mock_agent_run())
            MockAgent.return_value = mock_agent_instance

            events = []
            async for event in agent._run_async_impl(ctx):
                events.append(event)

            # Should evaluate, yield follow-up, increment turn count
            assert len(events) == 2
            assert events[0].content.parts[0].text == "How will you handle scaling?"
            assert events[1].actions.state_delta["phase_turn_count"] == 2

            # Verify evaluation was called
            tools.evaluate_phase.assert_called_once()

    @pytest.mark.asyncio
    async def test_subsequent_turn_evaluates_and_escalates(self):
        """Test subsequent turn with 'next_phase' decision: evaluates and escalates"""
        tools = Mock()
        tools.evaluate_phase = AsyncMock(
            return_value={
                "decision": "next_phase",
                "score": 1.0,
                "message": "Phase complete",
            }
        )
        tools.get_context = AsyncMock(return_value="Data design context")

        agent = PhaseAgent(tools, max_turns=5)

        class MockContext:
            session = Session(
                id="test",
                app_name="test",
                user_id="test",
                state={
                    "current_phase": "data_design",
                    "phase_turn_count": 2,
                    "interview_question": "Design a cache",
                },
                events=[],
            )

        ctx = MockContext()

        events = []
        async for event in agent._run_async_impl(ctx):
            events.append(event)

        # Should evaluate and escalate (no LLM follow-up)
        assert len(events) == 1
        assert events[0].actions.escalate is True
        assert events[0].actions.state_delta["phase_complete"] is True
        assert events[0].actions.state_delta["phase_turn_count"] == 0

        # Verify evaluation was called
        tools.evaluate_phase.assert_called_once()

    @pytest.mark.asyncio
    async def test_max_turns_forces_escalation(self):
        """Test max_turns reached forces escalation"""
        tools = Mock()
        tools.evaluate_phase = AsyncMock(
            return_value={
                "decision": "continue",
                "score": 0.5,
            }
        )
        tools.get_context = AsyncMock(return_value="Data design context")

        agent = PhaseAgent(tools, max_turns=3)

        class MockContext:
            session = Session(
                id="test",
                app_name="test",
                user_id="test",
                state={
                    "current_phase": "data_design",
                    "phase_turn_count": 3,  # At max turns
                    "interview_question": "Design a cache",
                },
                events=[],
            )

        ctx = MockContext()

        # Mock conversation agent
        with patch(
            "interview_orchestrator.interview_types.system_design.sub_agents.phase_agent.Agent"
        ) as MockAgent:

            async def mock_agent_run():
                yield Event(
                    author="phase_data_design_conversation",
                    content=Content(parts=[Part(text="Follow-up question")]),
                )

            mock_agent_instance = Mock()
            mock_agent_instance.run_async = Mock(return_value=mock_agent_run())
            MockAgent.return_value = mock_agent_instance

            events = []
            async for event in agent._run_async_impl(ctx):
                events.append(event)

            # Should yield follow-up, increment, then force escalation
            assert len(events) == 3
            assert events[0].content.parts[0].text == "Follow-up question"
            assert events[1].actions.state_delta["phase_turn_count"] == 4
            assert events[2].actions.escalate is True


class TestPhaseAgentIntegration:
    """Integration tests with real tool provider"""

    @pytest.mark.asyncio
    async def test_all_phases_have_valid_instructions(self):
        """Test instruction generation works for all phases"""
        tools = DefaultSystemDesignTools()
        agent = PhaseAgent(tools)
        phases = await tools.get_phases()

        class MockContext:
            session = Session(
                id="test",
                app_name="test",
                user_id="test",
                state={"interview_question": "Design a system"},
                events=[],
            )

        ctx = MockContext()

        for phase in phases:
            instruction = await agent._get_phase_instruction(ctx, phase["id"])
            assert len(instruction) > 0
            assert phase["id"] in instruction.lower()
