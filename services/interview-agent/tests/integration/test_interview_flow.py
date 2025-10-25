"""
Integration tests for the complete interview flow.

These tests use real ADK infrastructure (Runner, SessionService, etc.)
and use the record/replay pattern for LLM responses:
- First run with RECORD_MODE=true: Uses real LLM and saves responses
- Subsequent runs: Replays saved responses (no API calls, no cost)

To re-record responses after code changes:
    RECORD_MODE=true pytest tests/integration/test_interview_flow.py
"""

import pytest
import pytest_asyncio
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from interview_agent.agent import root_agent

from .llm_recorder import LLMRecorder


def create_user_message(text: str) -> Content:
    """Helper to create a user message Content object."""
    return Content(role="user", parts=[Part(text=text)])


@pytest.fixture
def session_service():
    """Create an in-memory session service for testing."""
    return InMemorySessionService()


@pytest.fixture
def runner(session_service):
    """Create a Runner with the root agent."""
    return Runner(
        app_name="test_interview_agent",
        agent=root_agent,
        session_service=session_service,
    )


@pytest_asyncio.fixture
async def test_session(session_service):
    """Create a test session."""
    return await session_service.create_session(
        user_id="test_user",
        app_name="test_interview_agent",
    )


class TestCompleteInterviewFlow:
    """Test the complete interview flow from start to finish."""

    @pytest.mark.asyncio
    async def test_full_interview_flow(self, runner, session_service, test_session):
        """
        Test complete CUJ: User goes through routing -> intro -> closing

        Uses record/replay pattern for LLM responses:
        - First run: RECORD_MODE=true to use real LLM and save responses
        - Subsequent runs: Replays saved responses (no API cost)
        """
        with LLMRecorder("test_full_interview_flow"):
            # ============================================================
            # Turn 1: Initial greeting
            # ============================================================
            events = []
            async for event in runner.run_async(
                user_id=test_session.user_id,
                session_id=test_session.id,
                new_message=create_user_message("hi"),
            ):
                events.append(event)

            # Verify agent asked for company
            assert len(events) > 0

            # Retrieve session to check state
            test_session = await session_service.get_session(
                app_name=test_session.app_name,
                user_id=test_session.user_id,
                session_id=test_session.id,
            )
            # Session state should still be empty (no routing yet)
            assert "routing_decision" not in test_session.state

            # ============================================================
            # Turn 2: User provides company and interview type
            # ============================================================
            events = []
            async for event in runner.run_async(
                user_id=test_session.user_id,
                session_id=test_session.id,
                new_message=create_user_message("Amazon system design"),
            ):
                events.append(event)

            # Retrieve session to check state
            test_session = await session_service.get_session(
                app_name=test_session.app_name,
                user_id=test_session.user_id,
                session_id=test_session.id,
            )
            # Verify routing decision was saved
            assert "routing_decision" in test_session.state
            assert test_session.state["routing_decision"]["company"] == "amazon"
            assert test_session.state["routing_decision"]["interview_type"] == "system_design"

            # ============================================================
            # Turn 3: Intro agent asks for name
            # ============================================================
            events = []
            async for event in runner.run_async(
                user_id=test_session.user_id,
                session_id=test_session.id,
                new_message=create_user_message("Let's start"),
            ):
                events.append(event)

            # Retrieve session to check state
            test_session = await session_service.get_session(
                app_name=test_session.app_name,
                user_id=test_session.user_id,
                session_id=test_session.id,
            )
            # Should still be in intro phase
            assert test_session.state.get("interview_phase", "intro") == "intro"
            assert "candidate_info" not in test_session.state

            # ============================================================
            # Turn 4: User provides all info, intro agent saves it
            # ============================================================
            events = []
            async for event in runner.run_async(
                user_id=test_session.user_id,
                session_id=test_session.id,
                new_message=create_user_message(
                    "My name is Alice, I have 5 years of experience in distributed systems "
                    "and backend, and I've worked on projects like a real-time messaging "
                    "system and API gateway"
                ),
            ):
                events.append(event)

            # Retrieve session to check state
            test_session = await session_service.get_session(
                app_name=test_session.app_name,
                user_id=test_session.user_id,
                session_id=test_session.id,
            )
            # Verify candidate info was saved
            assert "candidate_info" in test_session.state
            assert test_session.state["candidate_info"]["name"] == "Alice"

            # Verify phase transition to closing
            assert test_session.state.get("interview_phase") == "closing"

            # ============================================================
            # Turn 5: Closing agent wraps up
            # ============================================================
            events = []
            async for event in runner.run_async(
                user_id=test_session.user_id,
                session_id=test_session.id,
                new_message=create_user_message("Thanks!"),
            ):
                events.append(event)

            # Retrieve session to check state
            test_session = await session_service.get_session(
                app_name=test_session.app_name,
                user_id=test_session.user_id,
                session_id=test_session.id,
            )
            # Verify interview is done
            assert test_session.state.get("interview_phase") == "done"
