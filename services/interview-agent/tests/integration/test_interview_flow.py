"""
Integration tests for complete interview flow - Split by CUJ phases.

Tests the complete Critical User Journey broken down into 4 main tests:
1. Routing phase
2. Intro and candidate info retrieval
3. Design phases (multi-turn conversations, evaluation, transitions) - Local & Remote
4. Closing and completion

Each test uses LLM recording/replay for deterministic, cost-free testing.
Tests can piggyback on previous test recordings for flow continuity.
"""

import pytest
import pytest_asyncio
import respx
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from httpx import Response

from interview_agent.root_agent import RootCustomAgent
from interview_agent.shared.plugins import LoggingPlugin

from .providers.mock_remote_agent import MockA2AResponses
from .test_helpers import (
    create_session_with_candidate_info,
    create_session_with_routing,
    get_session_state,
    send_message,
)


@pytest.fixture
def session_service():
    """Create session service."""
    return InMemorySessionService()


@pytest.fixture
def runner(session_service):
    """Create runner with root agent and logging plugin.

    Logging is always enabled for integration tests to help diagnose issues.
    Logs only important events: tool calls, state changes, and errors.
    """
    return Runner(
        app_name="test_interview_agent",
        agent=RootCustomAgent(),
        session_service=session_service,
        plugins=[LoggingPlugin()],  # ✅ Always attached
    )


@pytest_asyncio.fixture
async def test_session(session_service):
    """Create test session."""
    return await session_service.create_session(
        user_id="test_user",
        app_name="test_interview_agent",
    )


@pytest.fixture
def mock_google_agent():
    """Mock Google remote agent A2A calls with respx.

    Only mocks localhost requests to avoid interfering with LLM API calls.
    """
    with respx.mock(assert_all_called=False, assert_all_mocked=False) as respx_mock:
        # IMPORTANT: Order matters! Specific routes FIRST, pass-through LAST
        # Mock ONLY localhost:10123 with url pattern (more specific than route())
        respx_mock.route(url__startswith="http://localhost:10123").mock(
            side_effect=[
                Response(200, json=MockA2AResponses.get_phases()),
                Response(200, json=MockA2AResponses.start_interview()),
                Response(200, json=MockA2AResponses.get_question()),
                Response(200, json=MockA2AResponses.get_context()),
                Response(200, json=MockA2AResponses.evaluate_phase_next()),
            ]
            * 20  # Repeat for multiple calls
        )

        # Allow all other requests (e.g., Gemini API) to pass through to real network
        respx_mock.route().pass_through()

        yield


@pytest.mark.integration
class TestRoutingPhase:
    """
    Test 1: Routing Phase

    Tests the initial routing conversation where user specifies:
    - Company preference (e.g., Amazon, Google, Meta)
    - Interview type (e.g., system_design, coding, behavioral)

    Record metrics: ~2-3 LLM calls, ~10-15 seconds
    """

    @pytest.mark.asyncio
    @pytest.mark.timeout(120)
    async def test_routing_decision(self, runner, session_service, test_session, mock_google_agent):
        """
        Test routing phase with multi-turn conversation.

        LLM Calls (Record): 3
        Time (Record): ~12 seconds
        """
        # Initial greeting - no routing decision yet
        await send_message(runner, test_session, "Hello!")
        state = await get_session_state(session_service, test_session)
        assert "routing_decision" not in state

        # User provides company and interview type
        await send_message(runner, test_session, "I want Google system design")
        state = await get_session_state(session_service, test_session)

        # Verify routing decision saved
        assert "routing_decision" in state
        assert state["routing_decision"]["company"] == "google"
        assert state["routing_decision"]["interview_type"] == "system_design"


@pytest.mark.integration
class TestIntroPhase:
    """
    Test 2: Intro and Candidate Info Retrieval

    Tests the intro agent collecting candidate background:
    - Name
    - Years of experience
    - Domain expertise
    - Notable projects

    Piggybacks on routing test recordings for flow continuity.

    Record metrics: ~4-5 LLM calls, ~20-25 seconds
    """

    @pytest.mark.asyncio
    @pytest.mark.timeout(120)
    async def test_intro_and_candidate_info(self, runner, session_service, mock_google_agent):
        """
        Test intro phase collecting candidate information.

        Manually sets routing state to bypass routing phase.
        Tests that LLM calls tools to save candidate info.

        LLM Calls: ~3-4 (intro only, no routing)
        Time: ~15-20 seconds
        """
        # Create session with routing decision pre-set (bypass routing phase)
        test_session = await create_session_with_routing(
            session_service,
            company="google",
            interview_type="system_design",
        )

        # Verify routing state is set
        state = await get_session_state(session_service, test_session)
        assert "routing_decision" in state
        assert state["routing_decision"]["company"] == "google"
        assert state["routing_decision"]["interview_type"] == "system_design"

        # Intro phase - multi-turn conversation
        await send_message(
            runner,
            test_session,
            "My name is Sarah Johnson, I have 8 years of professional experience",
        )
        state = await get_session_state(session_service, test_session)

        # May not have candidate_info yet if agent needs more details
        await send_message(
            runner,
            test_session,
            "My domain expertise is backend distributed systems. "
            "I scaled Netflix microservices to 100M users and built "
            "payment infrastructure at Stripe",
        )
        state = await get_session_state(session_service, test_session)

        # Verify candidate info saved by LLM and transitioned to design phase
        assert "candidate_info" in state, f"candidate_info not found in state: {state.keys()}"
        phase = state.get("interview_phase")
        assert phase == "design", f"Expected design phase, got: {phase}"

        # Verify candidate info details
        candidate_info = state["candidate_info"]
        assert "name" in candidate_info
        assert "years_experience" in candidate_info or "experience" in candidate_info


@pytest.mark.integration
class TestDesignPhase:
    """
    Test 3: Design Phase

    Tests design phases with multi-turn conversations.
    Uses helpers to bypass routing and intro phases.

    LLM Calls: ~6-8
    """

    @pytest.mark.asyncio
    @pytest.mark.timeout(120)
    async def test_design_phase(self, runner, session_service, mock_google_agent):
        """
        Test design phases with multi-turn conversations.

        Uses helper to inject routing + candidate_info state via EventActions,
        then tests first phase with 2 turns.

        LLM Calls: ~6-8 (design phase only, no routing/intro)
        """
        # Create session with routing + candidate_info already set via helper
        test_session = await create_session_with_candidate_info(
            session_service,
            company="google",
            interview_type="system_design",
            name="Sarah Johnson",
            years_experience=8,
            domain="backend distributed systems",
        )

        # Verify helper set state correctly
        state = await get_session_state(session_service, test_session)
        assert "routing_decision" in state
        assert "candidate_info" in state
        assert state.get("interview_phase") == "design"

        # Phase 1 - Turn 1: Initial design
        await send_message(
            runner,
            test_session,
            "I'll design a URL shortening service. "
            "For the high-level approach, I'd use a hash-based solution with a "
            "NoSQL database for storing mappings and a cache layer for frequent URLs.",
        )
        state = await get_session_state(session_service, test_session)

        # Should have current phase set
        assert "current_phase" in state
        current_phase = state.get("current_phase")
        print(f"Current phase after turn 1: {current_phase}")

        # Phase 1 - Turn 2: Add more details
        await send_message(
            runner,
            test_session,
            "For scalability, I'd use consistent hashing for sharding the data. "
            "The API would have POST /shorten and GET /{shortCode}. "
            "We'll need rate limiting to prevent abuse.",
        )
        state = await get_session_state(session_service, test_session)

        # Should have phase state and index
        assert "current_phase" in state
        assert "current_phase_idx" in state

        # May have completed first phase or still in it
        phase_idx = state.get("current_phase_idx", 0)
        print(f"Phase index after turn 2: {phase_idx}")
        print(f"Current phase: {state.get('current_phase')}")
        print(f"Phase complete: {state.get('phase_complete')}")
