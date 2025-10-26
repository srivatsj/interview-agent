"""
Integration tests for complete interview flow with mock tools.

Uses 3-phase mock to avoid API quota issues while testing full CUJ.
"""

import asyncio
from unittest.mock import patch

import pytest
import pytest_asyncio
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from interview_agent.root_agent import root_agent

from .llm_recorder import LLMRecorder
from .mock_tools import MockAmazonTools


def create_user_message(text: str) -> Content:
    """Helper to create user message."""
    return Content(role="user", parts=[Part(text=text)])


@pytest.fixture
def session_service():
    """Create session service."""
    return InMemorySessionService()


@pytest.fixture
def runner(session_service):
    """Create runner with root agent."""
    return Runner(
        app_name="test_interview_agent",
        agent=root_agent,
        session_service=session_service,
    )


@pytest_asyncio.fixture
async def test_session(session_service):
    """Create test session."""
    return await session_service.create_session(
        user_id="test_user",
        app_name="test_interview_agent",
    )


class TestCompleteInterviewFlow:
    """Test complete CUJ with all phases."""

    @pytest.mark.asyncio
    async def test_full_interview_flow(self, runner, session_service, test_session):
        """
        Test complete interview flow: routing → intro → design → closing → done

        Uses 2-phase mock (clarification, design) to avoid quota issues.
        Verifies all state transitions and phase progression.
        """
        with patch(
            "interview_agent.interview_types.system_design.system_design_agent.AmazonSystemDesignTools",
            MockAmazonTools,
        ):
            with LLMRecorder("test_full_interview_flow"):
                # ======================================
                # ROUTING PHASE
                # ======================================
                # Turn 1: Greeting
                async for _ in runner.run_async(
                    user_id=test_session.user_id,
                    session_id=test_session.id,
                    new_message=create_user_message("hi"),
                ):
                    pass

                test_session = await session_service.get_session(
                    app_name=test_session.app_name,
                    user_id=test_session.user_id,
                    session_id=test_session.id,
                )
                assert "routing_decision" not in test_session.state

                await asyncio.sleep(20)  # Wait for quota reset between turns

                # Turn 2: Select interview
                async for _ in runner.run_async(
                    user_id=test_session.user_id,
                    session_id=test_session.id,
                    new_message=create_user_message("Amazon system design"),
                ):
                    pass

                test_session = await session_service.get_session(
                    app_name=test_session.app_name,
                    user_id=test_session.user_id,
                    session_id=test_session.id,
                )
                assert test_session.state["routing_decision"]["company"] == "amazon"
                assert test_session.state["routing_decision"]["interview_type"] == "system_design"

                await asyncio.sleep(20)  # Wait for quota reset between turns

                # ======================================
                # INTRO PHASE
                # ======================================
                async for _ in runner.run_async(
                    user_id=test_session.user_id,
                    session_id=test_session.id,
                    new_message=create_user_message(
                        "I'm Alice, 5 years experience in distributed systems. " "Ready to start!"
                    ),
                ):
                    pass

                test_session = await session_service.get_session(
                    app_name=test_session.app_name,
                    user_id=test_session.user_id,
                    session_id=test_session.id,
                )
                # Should be in design phase (loop may have already progressed)
                assert test_session.state.get("interview_phase") == "design"
                assert test_session.state.get("current_phase_idx") >= 0

                await asyncio.sleep(20)  # Wait for quota reset between turns

                # ======================================
                # DESIGN PHASE 1: Clarification
                # ======================================
                async for _ in runner.run_async(
                    user_id=test_session.user_id,
                    session_id=test_session.id,
                    new_message=create_user_message(
                        "For scale, 100M users, 10k QPS, low latency, high availability"
                    ),
                ):
                    pass

                test_session = await session_service.get_session(
                    app_name=test_session.app_name,
                    user_id=test_session.user_id,
                    session_id=test_session.id,
                )
                # Should have completed clarification and moved to design (phase 1)
                assert test_session.state.get("current_phase_idx") >= 1

                await asyncio.sleep(20)  # Wait for quota reset between turns

                # ======================================
                # DESIGN PHASE 2: Design (final design phase)
                # ======================================
                async for _ in runner.run_async(
                    user_id=test_session.user_id,
                    session_id=test_session.id,
                    new_message=create_user_message(
                        "Use DynamoDB database with schema having shortCode as key. "
                        "Indexing on shortCode, sharding by hash. Add Redis cache "
                        "for performance."
                    ),
                ):
                    pass

                test_session = await session_service.get_session(
                    app_name=test_session.app_name,
                    user_id=test_session.user_id,
                    session_id=test_session.id,
                )

                # All 2 design phases complete
                assert test_session.state.get("current_phase_idx") == 2
                assert test_session.state.get("interview_phases_complete") is True
                assert test_session.state.get("interview_phase") == "closing"

                await asyncio.sleep(20)  # Wait for quota reset between turns

                # ======================================
                # CLOSING PHASE
                # ======================================
                async for _ in runner.run_async(
                    user_id=test_session.user_id,
                    session_id=test_session.id,
                    new_message=create_user_message("Thank you! Great discussion."),
                ):
                    pass

                test_session = await session_service.get_session(
                    app_name=test_session.app_name,
                    user_id=test_session.user_id,
                    session_id=test_session.id,
                )
                assert test_session.state.get("interview_phase") == "done"

                # ======================================
                # FINAL VERIFICATION
                # ======================================
                # Verify complete flow succeeded
                assert test_session.state["routing_decision"]["company"] == "amazon"
                assert test_session.state["interview_phases_complete"] is True
                assert test_session.state["interview_phase"] == "done"
                assert test_session.state["current_phase_idx"] == 2
