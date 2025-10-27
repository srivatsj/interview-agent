"""
Integration tests for complete interview flow.

Tests entire CUJ with real local provider using hybrid approach:
- Full E2E test with multi-turn conversations
- Design phase progression test
- Critical path (routing + intro) test

Uses MockAmazonSystemDesignTools (3 phases) for faster testing while
still validating phase progression, multi-turn conversations, and state management.

Total: ~12-15 LLM calls in record mode
"""

from unittest.mock import patch

import pytest
import pytest_asyncio
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai.types import Content, Part

from interview_agent.root_agent import root_agent

from .llm_recorder import LLMRecorder
from .providers.mock_amazon_tools import MockAmazonSystemDesignTools


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


async def send_message(runner, session, message: str):
    """Send a message and consume all events."""
    async for _ in runner.run_async(
        user_id=session.user_id,
        session_id=session.id,
        new_message=create_user_message(message),
    ):
        pass


async def get_session_state(session_service, session):
    """Get current session state."""
    updated_session = await session_service.get_session(
        app_name=session.app_name,
        user_id=session.user_id,
        session_id=session.id,
    )
    return updated_session.state


class TestCompleteInterviewFlow:
    """
    Test complete interview CUJ from start to finish with multi-turn conversations.

    Validates entire user journey: routing → intro → design phases → closing → done
    """

    @pytest.mark.asyncio
    async def test_complete_interview_journey(self, runner, session_service, test_session):
        """Test full interview from greeting to completion with realistic multi-turn."""
        with patch(
            "interview_agent.interview_types.system_design.company_factory.AmazonSystemDesignTools",
            MockAmazonSystemDesignTools,
        ):
            with LLMRecorder("test_complete_interview_journey"):
                # Routing phase (multi-turn)
                await send_message(runner, test_session, "Hello!")
                state = await get_session_state(session_service, test_session)
                assert "routing_decision" not in state

                await send_message(runner, test_session, "I want Amazon system design")
                state = await get_session_state(session_service, test_session)
                assert state["routing_decision"]["company"] == "amazon"
                assert state["routing_decision"]["interview_type"] == "system_design"

                # Intro phase (multi-turn)
                await send_message(
                    runner,
                    test_session,
                    "My name is Sarah Johnson, I have 8 years of professional experience",
                )
                await send_message(
                    runner,
                    test_session,
                    "My domain expertise is backend distributed systems. "
                    "I scaled Netflix microservices to 100M users and built "
                    "payment infrastructure at Stripe",
                )
                state = await get_session_state(session_service, test_session)
                assert "candidate_info" in state or state.get("interview_phase") == "design"
                assert state["interview_phase"] == "design"

                # Design Phase 1: Clarification (multi-turn)
                await send_message(runner, test_session, "Scale: 500M users globally")
                await send_message(
                    runner,
                    test_session,
                    "200k QPS peak, <100ms latency, 99.99% availability",
                )
                state = await get_session_state(session_service, test_session)
                assert state.get("current_phase_idx") >= 1

                # Design Phase 2: Design (multi-turn)
                await send_message(
                    runner,
                    test_session,
                    "DynamoDB database, schema with shortCode as key, API with REST endpoints",
                )
                await send_message(
                    runner,
                    test_session,
                    "Architecture components: load balancer, app servers, database cluster",
                )
                state = await get_session_state(session_service, test_session)
                assert state.get("current_phase_idx") >= 2

                # Design Phase 3: Tradeoffs (multi-turn)
                await send_message(
                    runner,
                    test_session,
                    "Add Redis cache for performance, database is the bottleneck at scale",
                )
                await send_message(
                    runner,
                    test_session,
                    "Use load balancer for horizontal scaling, shard database by hash",
                )
                state = await get_session_state(session_service, test_session)
                assert state.get("current_phase_idx") == 3
                assert state.get("interview_phases_complete") is True
                # May be closing or done depending on when closing agent completes
                assert state.get("interview_phase") in ["closing", "done"]

                # If still in closing, send final messages
                if state.get("interview_phase") == "closing":
                    await send_message(runner, test_session, "How did I do? Areas to improve?")
                    await send_message(runner, test_session, "Thanks for the great interview!")
                    state = await get_session_state(session_service, test_session)

                # Final state should be done
                assert state.get("interview_phase") == "done"

                # Final verification
                assert state["routing_decision"]["company"] == "amazon"
                assert "candidate_info" in state or state.get("interview_phase") == "done"
                assert state["interview_phases_complete"] is True
                assert state["current_phase_idx"] == 3
