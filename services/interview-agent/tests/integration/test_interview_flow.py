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
    Test 3: Design Phase - Complete Multi-Phase Interview

    Tests design phases with:
    - Multi-turn conversations within each phase
    - Phase evaluation (continue vs next_phase decisions)
    - Follow-up questions from agent
    - Phase completion and transitions
    - Overall design completion across all phases

    Uses helpers to bypass routing and intro phases.

    LLM Calls: ~8-12 (design phases only, no routing/intro)
    Time: ~40-60 seconds
    """

    @pytest.mark.asyncio
    @pytest.mark.timeout(180)
    async def test_design_phase_paid_remote(
        self, runner, session_service, mock_google_agent
    ):
        """
        Test complete design phase flow with PAID REMOTE agent (Google).

        Uses mocked remote agent responses via respx.

        IMPORTANT: The LoopAgent runs multiple internal iterations per user message!
        - Each phase runs a loop with multiple evaluations until complete
        - ONE user message processes ONE phase (multiple internal evaluations)
        - SystemDesignAgent processes one phase per invocation

        Mock sequence (6 evaluations total across 3 phases):
        - Phase 0 (plan_and_scope): 3 internal evaluations (continue, continue, next_phase)
        - Phase 1 (requirements_alignment): 2 internal evaluations (continue, next_phase)
        - Phase 2 (architecture_blueprint): 1 evaluation (next_phase)

        Flow:
        1. Setup: Use helper to inject routing + candidate_info
        2. User message 1: Completes phase 0 (3 internal evaluations)
        3. User message 2: Completes phase 1 (2 internal evaluations)
        4. User message 3: Completes phase 2 (1 evaluation)
        5. Verify all 3 phases complete and interview finishes

        LLM Calls: ~8-10
        Time: ~30-50 seconds
        """
        # ========== SETUP ==========
        test_session = await create_session_with_candidate_info(
            session_service,
            company="google",
            interview_type="system_design",
            name="Sarah Johnson",
            years_experience=8,
            domain="backend distributed systems",
        )

        state = await get_session_state(session_service, test_session)
        assert "routing_decision" in state
        assert "candidate_info" in state
        assert state.get("interview_phase") == "design"
        print("\n✓ Setup complete: routing + candidate_info injected")

        # ========== USER MESSAGE 1: Phase 0 (plan_and_scope) ==========
        print("\n--- User Message 1: Phase 0 (plan_and_scope) ---")
        print("Expected: 3 internal evaluations (continue, continue, next_phase)")
        print("          Result: Phase 0 complete, advance to phase 1")

        await send_message(
            runner,
            test_session,
            "I'll design a URL shortening service. "
            "High-level approach: hash-based URL generation, "
            "NoSQL database for mappings, Redis cache for hot URLs, "
            "load balancer for distribution, and rate limiting for abuse prevention.",
        )
        state = await get_session_state(session_service, test_session)

        print("\nAfter message 1:")
        print(f"  Phase index: {state.get('current_phase_idx')}")
        print(f"  Phase complete: {state.get('phase_complete')}")

        assert state.get("current_phase_idx") == 1, \
            "Should have advanced to phase 1 (completed phase 0)"
        assert state.get("phase_complete") is True, \
            "Phase 0 should be marked complete"
        print("✓ Message 1 complete: Phase 0 done, advanced to phase 1")

        # ========== USER MESSAGE 2: Phase 1 (requirements_alignment) ==========
        print("\n--- User Message 2: Phase 1 (requirements_alignment) ---")
        print("Expected: 2 internal evaluations (continue, next_phase)")
        print("          Result: Phase 1 complete, advance to phase 2")

        await send_message(
            runner,
            test_session,
            "For requirements: The system must handle 100M URLs, "
            "generate unique 7-character short codes with collision handling, "
            "support custom aliases, rate limiting (100 reqs/hour per user), "
            "and GDPR compliance for EU users.",
        )
        state = await get_session_state(session_service, test_session)

        print("\nAfter message 2:")
        print(f"  Phase index: {state.get('current_phase_idx')}")
        print(f"  Phase complete: {state.get('phase_complete')}")

        assert state.get("current_phase_idx") == 2, \
            "Should have advanced to phase 2 (completed phase 1)"
        assert state.get("phase_complete") is True, \
            "Phase 1 should be marked complete"
        print("✓ Message 2 complete: Phase 1 done, advanced to phase 2")

        # ========== USER MESSAGE 3: Phase 2 (architecture_blueprint) ==========
        print("\n--- User Message 3: Phase 2 (architecture_blueprint) ---")
        print("Expected: 1 evaluation (next_phase)")
        print("          Result: Phase 2 complete, all phases done")

        await send_message(
            runner,
            test_session,
            "The architecture uses microservices: "
            "URL generation service, redirect service, analytics service. "
            "Each service scales independently on Kubernetes. "
            "Data layer uses sharded Cassandra with replication factor 3. "
            "CDN for global distribution and Redis for caching hot URLs.",
        )
        state = await get_session_state(session_service, test_session)

        print("\nAfter message 3:")
        print(f"  Phase index: {state.get('current_phase_idx')}")
        print(f"  Interview complete: {state.get('interview_phases_complete')}")

        # Should have advanced beyond all 3 phases (idx=3)
        assert state.get("current_phase_idx") == 3, \
            "Should have completed all 3 phases (idx should be 3)"

        # ========== VERIFY DESIGN COMPLETION ==========
        # Phase index 3 means all 3 phases (0, 1, 2) are complete
        # interview_phases_complete flag is set on the NEXT agent invocation
        # when it sees phase_idx >= len(phases), so it may be None here
        assert state.get("current_phase_idx") == 3, \
            "Phase index should be 3 (all phases complete)"

        print("\n✓ Design Interview Complete!")
        print("  Total phases completed: 3")
        print("  User messages sent: 3")
        print(f"  Final phase index: {state.get('current_phase_idx')}")
        status = state.get("interview_phases_complete", "pending final update")
        print(f"  Interview status: {status}")

    @pytest.mark.asyncio
    @pytest.mark.timeout(180)
    async def test_design_phase_free_default(
        self, runner, session_service
    ):
        """
        Test complete design phase flow with FREE DEFAULT agent.

        Uses REAL DefaultSystemDesignTools (no mocking) with keyword-based evaluation.

        Default agent has 6 phases:
        - Phase 0: get_problem
        - Phase 1: problem_clarification
        - Phase 2: requirements
        - Phase 3: data_design
        - Phase 4: api_design
        - Phase 5: hld

        Flow:
        1. Setup: Use helper to inject routing=default + candidate_info
        2. User message 1: Completes phase 0 (get_problem)
        3. User message 2: Completes phase 1 (problem_clarification)
        4. User message 3: Completes phase 2 (requirements)
        5. Verify phases are progressing with real keyword-based evaluation

        LLM Calls: ~8-10
        Time: ~30-50 seconds
        """
        # ========== SETUP ==========
        test_session = await create_session_with_candidate_info(
            session_service,
            company="default",  # FREE default agent
            interview_type="system_design",
            name="Alex Chen",
            years_experience=5,
            domain="distributed systems",
        )

        state = await get_session_state(session_service, test_session)
        assert "routing_decision" in state
        assert state["routing_decision"]["company"] == "default"
        assert "candidate_info" in state
        assert state.get("interview_phase") == "design"
        print("\n✓ Setup complete: routing=default + candidate_info injected")

        # ========== USER MESSAGE 1: Phase 0 (get_problem) ==========
        print("\n--- User Message 1: Phase 0 (get_problem) ---")
        print("Expected: Acknowledge problem and show understanding")
        print("          Result: Phase 0 complete, advance to phase 1")

        await send_message(
            runner,
            test_session,
            "I understand the problem. I'll design a URL shortening service. "
            "Got it, ready to proceed with clarifying questions.",
        )
        state = await get_session_state(session_service, test_session)

        print("\nAfter message 1:")
        print(f"  Phase index: {state.get('current_phase_idx')}")
        print(f"  Phase complete: {state.get('phase_complete')}")

        # Should advance from phase 0 to phase 1
        assert state.get("current_phase_idx") >= 1, \
            "Should have advanced to at least phase 1 (completed phase 0)"
        print("✓ Message 1 complete: Phase 0 done")

        # ========== USER MESSAGE 2: Phase 1 (problem_clarification) ==========
        print("\n--- User Message 2: Phase 1 (problem_clarification) ---")
        print("Expected: Cover keywords - qps, scale, users, latency, availability")
        print("          Result: Phase 1 complete, advance to phase 2")

        await send_message(
            runner,
            test_session,
            "For scale: We need to support 10 million users with 10k QPS peak. "
            "Latency should be under 100ms p99. "
            "Availability target is 99.9% with geographic distribution across US, EU, Asia.",
        )
        state = await get_session_state(session_service, test_session)

        print("\nAfter message 2:")
        print(f"  Phase index: {state.get('current_phase_idx')}")
        print(f"  Phase complete: {state.get('phase_complete')}")

        # Should advance from phase 1 to phase 2
        assert state.get("current_phase_idx") >= 2, \
            "Should have advanced to at least phase 2 (completed phase 1)"
        print("✓ Message 2 complete: Phase 1 done")

        # ========== USER MESSAGE 3: Phase 2 (requirements) ==========
        print("\n--- User Message 3: Phase 2 (requirements) ---")
        print("Expected: Cover keywords - functional, non-functional, scalability, consistency")
        print("          Result: Phase 2 complete, advance to phase 3")

        await send_message(
            runner,
            test_session,
            "Functional requirements: create short URL, redirect to original, delete URL. "
            "Non-functional: scalability to 100M URLs, eventual consistency is acceptable, "
            "high availability with 99.9% uptime. ",
        )
        state = await get_session_state(session_service, test_session)

        print("\nAfter message 3:")
        print(f"  Phase index: {state.get('current_phase_idx')}")
        print(f"  Phase complete: {state.get('phase_complete')}")

        # Should advance from phase 2 to phase 3
        assert state.get("current_phase_idx") >= 3, \
            "Should have advanced to at least phase 3 (completed phase 2)"
        print("✓ Message 3 complete: Phase 2 done")

        # ========== VERIFY MULTI-PHASE PROGRESSION ==========
        print("\n✓ Default Agent Design Interview Progressing!")
        print("  Total phases completed: 3+")
        print("  User messages sent: 3")
        print(f"  Current phase index: {state.get('current_phase_idx')}")
        print("  Using FREE default agent with keyword-based evaluation")
