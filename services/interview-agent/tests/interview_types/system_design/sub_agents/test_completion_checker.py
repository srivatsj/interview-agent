"""Tests for PhaseCompletionChecker"""

from unittest.mock import AsyncMock, Mock

import pytest
from google.adk.events import Event
from google.adk.sessions import Session
from google.genai.types import Content, Part

from interview_agent.interview_types.system_design.sub_agents import (
    PhaseCompletionChecker,
)
from interview_agent.interview_types.system_design.tools import DefaultSystemDesignTools


class TestPhaseCompletionChecker:
    """Test PhaseCompletionChecker initialization and basic functionality"""

    def test_initialization(self):
        """Test checker initializes correctly"""
        tools = DefaultSystemDesignTools()
        checker = PhaseCompletionChecker(tools)

        assert checker.name == "phase_completion_checker"
        assert checker.tool_provider == tools

    def test_extract_conversation_history_empty(self):
        """Test extraction with no events"""
        tools = DefaultSystemDesignTools()
        checker = PhaseCompletionChecker(tools)

        class MockContext:
            session = Session(
                id="test",
                app_name="test",
                user_id="test",
                state={},
                events=[],
            )

        ctx = MockContext()
        history = checker._extract_conversation_history(ctx)

        assert history == []

    def test_extract_conversation_history_with_messages(self):
        """Test extraction with multiple messages"""
        tools = DefaultSystemDesignTools()
        checker = PhaseCompletionChecker(tools)

        class MockContext:
            session = Session(
                id="test",
                app_name="test",
                user_id="test",
                state={},
                events=[
                    Event(
                        author="user",
                        content=Content(parts=[Part(text="Hello")]),
                    ),
                    Event(
                        author="assistant",
                        content=Content(parts=[Part(text="Hi there")]),
                    ),
                ],
            )

        ctx = MockContext()
        history = checker._extract_conversation_history(ctx)

        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert history[0]["content"] == "Hello"
        assert history[1]["role"] == "assistant"

    @pytest.mark.asyncio
    async def test_run_with_phase_complete(self):
        """Test checker escalates when phase is complete"""
        tools = Mock()
        tools.evaluate_phase = AsyncMock(
            return_value={
                "decision": "next_phase",
                "score": 8,
                "message": "Phase complete",
            }
        )
        checker = PhaseCompletionChecker(tools)

        class MockContext:
            session = Session(
                id="test",
                app_name="test",
                user_id="test",
                state={"current_phase": "data_design"},
                events=[],
            )

        ctx = MockContext()
        events = []
        async for event in checker._run_async_impl(ctx):
            events.append(event)

        assert len(events) == 1
        assert events[0].actions.escalate is True
        assert events[0].actions.state_delta["phase_complete"] is True
        assert ctx.session.state["phase_turn_count"] == 1

    @pytest.mark.asyncio
    async def test_run_with_phase_incomplete(self):
        """Test checker continues when phase incomplete"""
        tools = Mock()
        tools.evaluate_phase = AsyncMock(
            return_value={
                "decision": "continue",
                "score": 3,
                "gaps": ["scalability"],
                "followup_questions": "What about scale?",
            }
        )
        checker = PhaseCompletionChecker(tools)

        class MockContext:
            session = Session(
                id="test",
                app_name="test",
                user_id="test",
                state={"current_phase": "problem_clarification"},
                events=[],
            )

        ctx = MockContext()
        events = []
        async for event in checker._run_async_impl(ctx):
            events.append(event)

        assert len(events) == 1
        assert events[0].actions.escalate is not True
        assert ctx.session.state["phase_turn_count"] == 1

    @pytest.mark.asyncio
    async def test_turn_count_increments(self):
        """Test turn count increments on each check"""
        tools = Mock()
        tools.evaluate_phase = AsyncMock(return_value={"decision": "continue", "score": 2})
        checker = PhaseCompletionChecker(tools)

        class MockContext:
            session = Session(
                id="test",
                app_name="test",
                user_id="test",
                state={"current_phase": "data_design", "phase_turn_count": 2},
                events=[],
            )

        ctx = MockContext()
        async for _ in checker._run_async_impl(ctx):
            pass

        assert ctx.session.state["phase_turn_count"] == 3
