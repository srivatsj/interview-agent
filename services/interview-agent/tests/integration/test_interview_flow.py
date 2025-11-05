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

import json
from pathlib import Path

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
    Provides realistic sequence: get_phases -> get_context -> get_question ->
    evaluate (continue x2, then next_phase) for each phase.
    """
    with respx.mock(assert_all_called=False, assert_all_mocked=False) as respx_mock:
        # IMPORTANT: Order matters! Specific routes FIRST, pass-through LAST
        # Mock ONLY localhost:10123 with url pattern (more specific than route())

        # Create a realistic sequence for multi-phase interview
        # NOTE: Conversation agent has no tools, so get_question() is NOT called
        # Sequence: get_phases -> get_context (per phase) -> evaluate_phase (per turn)
        #
        # Phase 1: get_phases, get_context, evaluate (continue, continue, next_phase)
        # Phase 2: get_context, evaluate (continue), evaluate (next_phase)
        # Phase 3: get_context, evaluate (next_phase)
        response_sequence = [
            # Initial setup: Get all phases and context for phase 1
            Response(200, json=MockA2AResponses.get_phases()),  # 0
            Response(200, json=MockA2AResponses.get_context()),  # 1: Phase 1 context
            # Phase 1 evaluations (after each user turn)
            Response(200, json=MockA2AResponses.evaluate_phase_continue()),  # 2: Turn 1 - continue
            Response(200, json=MockA2AResponses.evaluate_phase_continue()),  # 3: Turn 2 - continue
            Response(200, json=MockA2AResponses.evaluate_phase_next()),  # 4: Turn 3 - next_phase
            # Phase 2 setup and evaluations
            Response(200, json=MockA2AResponses.get_context()),  # 5: Phase 2 context
            Response(200, json=MockA2AResponses.evaluate_phase_continue()),  # 6: Turn 1 - continue
            Response(200, json=MockA2AResponses.evaluate_phase_next()),  # 7: Turn 2 - next_phase
            # Phase 3 setup and evaluation
            Response(200, json=MockA2AResponses.get_context()),  # 8: Phase 3 context
            Response(200, json=MockA2AResponses.evaluate_phase_next()),  # 9: Turn 1 - next_phase
        ]

        # Repeat sequence to handle multiple test runs
        respx_mock.route(url__startswith="http://localhost:10123").mock(
            side_effect=response_sequence * 10
        )

        # Allow all other requests (e.g., Gemini API) to pass through to real network
        respx_mock.route().pass_through()

        yield


@pytest_asyncio.fixture(autouse=True)
async def log_conversation(session_service, request):
    """Automatically log full conversation after each test."""
    sessions_to_log = []

    # Store original create_session to intercept session creation
    original_create = session_service.create_session

    async def track_session(*args, **kwargs):
        session = await original_create(*args, **kwargs)
        sessions_to_log.append(session)
        return session

    session_service.create_session = track_session

    yield  # Run test

    # Restore original method
    session_service.create_session = original_create

    # Save conversations in tests/integration/recording
    recording_dir = Path(__file__).parent / "recording"
    recording_dir.mkdir(exist_ok=True)

    for session in sessions_to_log:
        # Fetch latest session data
        updated_session = await session_service.get_session(
            app_name=session.app_name,
            user_id=session.user_id,
            session_id=session.id,
        )

        conversation = []
        for event in updated_session.events:
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        conversation.append({"role": event.author, "text": part.text})

        if conversation:
            # Use test method name to avoid overwriting
            filepath = recording_dir / f"{request.node.name}.json"
            with open(filepath, "w") as f:
                json.dump(conversation, f, indent=2)


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
    async def test_routing_decision_paid_remote(
        self, runner, session_service, test_session, mock_google_agent
    ):
        """
        Test routing phase to paid remote agent (Google).

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

    @pytest.mark.asyncio
    @pytest.mark.timeout(120)
    async def test_routing_decision_free_default(self, runner, session_service, test_session):
        """
        Test routing phase to free default agent.

        LLM Calls (Record): 3
        Time (Record): ~12 seconds
        """
        # Initial greeting - no routing decision yet
        await send_message(runner, test_session, "Hello!")
        state = await get_session_state(session_service, test_session)
        assert "routing_decision" not in state

        # User provides company and interview type
        await send_message(runner, test_session, "I want default system design")
        state = await get_session_state(session_service, test_session)

        # Verify routing decision saved
        assert "routing_decision" in state
        assert state["routing_decision"]["company"] == "default"
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

        # Intro phase - trigger intro agent to speak first
        # Send empty message to invoke intro agent and get LLM's greeting
        await send_message(runner, test_session, "")

        # Now respond to LLM's greeting with candidate info
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
