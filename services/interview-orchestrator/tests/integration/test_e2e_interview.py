"""
End-to-End Integration Tests with LLM-generated Candidate Responses

Tests the complete interview flow from routing to completion using
an LLM to generate realistic candidate responses. This enables:
- Natural multi-turn conversations
- No hardcoded responses
- Realistic testing of actual user experience
- Full conversation recordings

LLM Call Tracking:
Each test tracks and reports the total number of LLM calls made during execution.
This helps monitor test costs and execution time.
"""

import json
from pathlib import Path

import pytest
import pytest_asyncio
import respx
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from httpx import Response

from interview_orchestrator.root_agent import RootCustomAgent
from interview_orchestrator.shared.plugins import LoggingPlugin

from .providers.mock_remote_agent import MockA2AResponses
from .test_helpers import (
    CandidateResponseGenerator,
    get_last_agent_message,
    get_session_state,
    send_message,
)


@pytest.fixture
def session_service():
    """Create session service."""
    return InMemorySessionService()


@pytest.fixture
def runner(session_service):
    """Create runner with root agent and logging plugin."""
    return Runner(
        app_name="test_interview_orchestrator",
        agent=RootCustomAgent(),
        session_service=session_service,
        plugins=[LoggingPlugin()],
    )


@pytest_asyncio.fixture
async def test_session(session_service):
    """Create test session."""
    return await session_service.create_session(
        user_id="test_user",
        app_name="test_interview_orchestrator",
    )


@pytest.fixture
def mock_google_agent():
    """Mock Google remote agent A2A calls with respx."""
    with respx.mock(assert_all_called=False, assert_all_mocked=False) as respx_mock:
        # Create a realistic sequence for multi-phase interview
        response_sequence = [
            # Initial setup
            Response(200, json=MockA2AResponses.get_phases()),
            Response(200, json=MockA2AResponses.get_context()),
            # Phase 0: 3 evaluations (continue, continue, next_phase)
            Response(200, json=MockA2AResponses.evaluate_phase_continue()),
            Response(200, json=MockA2AResponses.evaluate_phase_continue()),
            Response(200, json=MockA2AResponses.evaluate_phase_next()),
            # Phase 1: 2 evaluations (continue, next_phase)
            Response(200, json=MockA2AResponses.get_context()),
            Response(200, json=MockA2AResponses.evaluate_phase_continue()),
            Response(200, json=MockA2AResponses.evaluate_phase_next()),
            # Phase 2: 1 evaluation (next_phase)
            Response(200, json=MockA2AResponses.get_context()),
            Response(200, json=MockA2AResponses.evaluate_phase_next()),
        ]

        respx_mock.route(url__startswith="http://localhost:10123").mock(
            side_effect=response_sequence * 10
        )

        respx_mock.route().pass_through()

        yield


@pytest_asyncio.fixture(autouse=True)
async def log_conversation(session_service, request):
    """Automatically log full conversation after each test."""
    sessions_to_log = []

    original_create = session_service.create_session

    async def track_session(*args, **kwargs):
        session = await original_create(*args, **kwargs)
        sessions_to_log.append(session)
        return session

    session_service.create_session = track_session

    yield

    session_service.create_session = original_create

    recording_dir = Path(__file__).parent / "recording"
    recording_dir.mkdir(exist_ok=True)

    for session in sessions_to_log:
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
            filepath = recording_dir / f"{request.node.name}.json"
            with open(filepath, "w") as f:
                json.dump(conversation, f, indent=2)


@pytest.mark.integration
class TestE2EInterview:
    """
    End-to-End Interview Tests

    Tests complete interview flow with LLM-generated candidate responses:
    - Routing phase
    - Intro phase (multi-turn)
    - Design phases (multi-turn for each phase)
    - Natural conversation flow
    - Realistic candidate behavior
    """

    @pytest.mark.asyncio
    @pytest.mark.timeout(600)
    async def test_e2e_interview_free_default(self, runner, session_service, test_session):
        """
        Complete E2E test with FREE DEFAULT agent using LLM-generated responses.

        Flow:
        1. Routing: User states preference
        2. Intro: Multi-turn conversation collecting candidate info
        3. Design: Multi-turn conversations for each phase (5 phases total)
        4. Closing: Thank you, questions, and goodbye
        5. All responses generated by LLM to simulate real candidate

        Expected LLM calls: ~25-35 (interviewer + candidate)
        Time: ~2-4 minutes
        """
        candidate = CandidateResponseGenerator()
        candidate_profile = {
            "name": "Alex Chen",
            "years_experience": 5,
            "domain": "distributed systems",
        }

        total_interviewer_calls = 0  # Track interviewer LLM calls
        print("\n" + "=" * 80)
        print("E2E TEST: Free Default Agent")
        print("=" * 80)

        # ========== ROUTING PHASE ==========
        print("\n[ROUTING PHASE]")

        await send_message(runner, test_session, "Hello!")
        total_interviewer_calls += 1
        interviewer_msg = await get_last_agent_message(session_service, test_session)
        print(f"Interviewer: {interviewer_msg[:100]}...")

        # Candidate responds with preference
        candidate_msg = await candidate.generate_response(
            interviewer_msg, "routing", candidate_profile
        )
        await send_message(runner, test_session, candidate_msg)
        total_interviewer_calls += 1
        print(f"Candidate: {candidate_msg}")

        state = await get_session_state(session_service, test_session)
        assert "routing_decision" in state
        assert state["routing_decision"]["company"] == "default"
        print("✓ Routing complete")

        # ========== INTRO PHASE (Multi-turn) ==========
        print("\n[INTRO PHASE]")

        # Turn 1: Name and experience
        interviewer_msg = await get_last_agent_message(session_service, test_session)
        print(f"Interviewer: {interviewer_msg[:100]}...")

        candidate_msg = await candidate.generate_response(
            interviewer_msg, "intro_name", candidate_profile
        )
        await send_message(runner, test_session, candidate_msg)
        total_interviewer_calls += 1
        print(f"Candidate: {candidate_msg}")

        # Turn 2: Domain expertise
        interviewer_msg = await get_last_agent_message(session_service, test_session)
        print(f"Interviewer: {interviewer_msg[:100]}...")

        candidate_msg = await candidate.generate_response(
            interviewer_msg, "intro_domain", candidate_profile
        )
        await send_message(runner, test_session, candidate_msg)
        total_interviewer_calls += 1
        print(f"Candidate: {candidate_msg}")

        state = await get_session_state(session_service, test_session)
        assert "candidate_info" in state
        assert state.get("interview_phase") == "design"
        print("✓ Intro complete, moving to design")

        # ========== DESIGN PHASE (Multi-turn per phase) ==========
        print("\n[DESIGN PHASE]")

        # Phase 0: problem_clarification (2-3 turns)
        print("\n[Phase 0: problem_clarification]")
        for turn in range(2):
            interviewer_msg = await get_last_agent_message(session_service, test_session)
            print(f"  Turn {turn + 1} Interviewer: {interviewer_msg[:80]}...")

            candidate_msg = await candidate.generate_response(
                interviewer_msg, "problem_clarification", candidate_profile
            )
            await send_message(runner, test_session, candidate_msg)
            total_interviewer_calls += 1
            print(f"  Turn {turn + 1} Candidate: {candidate_msg[:80]}...")

            state = await get_session_state(session_service, test_session)
            if state.get("current_phase_idx", 0) > 0:
                print("  ✓ Phase 0 complete")
                break

        # Phase 1: requirements (2 turns)
        print("\n[Phase 1: requirements]")
        for turn in range(2):
            interviewer_msg = await get_last_agent_message(session_service, test_session)
            print(f"  Turn {turn + 1} Interviewer: {interviewer_msg[:80]}...")

            candidate_msg = await candidate.generate_response(
                interviewer_msg, "requirements", candidate_profile
            )
            await send_message(runner, test_session, candidate_msg)
            total_interviewer_calls += 1
            print(f"  Turn {turn + 1} Candidate: {candidate_msg[:80]}...")

            state = await get_session_state(session_service, test_session)
            if state.get("current_phase_idx", 0) > 1:
                print("  ✓ Phase 1 complete")
                break

        # Phase 2: data_design (2 turns)
        print("\n[Phase 2: data_design]")
        for turn in range(2):
            interviewer_msg = await get_last_agent_message(session_service, test_session)
            print(f"  Turn {turn + 1} Interviewer: {interviewer_msg[:80]}...")

            candidate_msg = await candidate.generate_response(
                interviewer_msg, "data_design", candidate_profile
            )
            await send_message(runner, test_session, candidate_msg)
            total_interviewer_calls += 1
            print(f"  Turn {turn + 1} Candidate: {candidate_msg[:80]}...")

            state = await get_session_state(session_service, test_session)
            if state.get("current_phase_idx", 0) > 2:
                print("  ✓ Phase 2 complete")
                break

        # Phase 3: api_design (2 turns)
        print("\n[Phase 3: api_design]")
        for turn in range(2):
            interviewer_msg = await get_last_agent_message(session_service, test_session)
            print(f"  Turn {turn + 1} Interviewer: {interviewer_msg[:80]}...")

            candidate_msg = await candidate.generate_response(
                interviewer_msg, "api_design", candidate_profile
            )
            await send_message(runner, test_session, candidate_msg)
            total_interviewer_calls += 1
            print(f"  Turn {turn + 1} Candidate: {candidate_msg[:80]}...")

            state = await get_session_state(session_service, test_session)
            if state.get("current_phase_idx", 0) > 3:
                print("  ✓ Phase 3 complete")
                break

        # Phase 4: hld (2 turns)
        print("\n[Phase 4: hld]")
        for turn in range(2):
            interviewer_msg = await get_last_agent_message(session_service, test_session)
            print(f"  Turn {turn + 1} Interviewer: {interviewer_msg[:80]}...")

            candidate_msg = await candidate.generate_response(
                interviewer_msg, "hld", candidate_profile
            )
            await send_message(runner, test_session, candidate_msg)
            total_interviewer_calls += 1
            print(f"  Turn {turn + 1} Candidate: {candidate_msg[:80]}...")

            state = await get_session_state(session_service, test_session)
            if state.get("current_phase_idx", 0) > 4:
                print("  ✓ Phase 4 complete")
                break

        # ========== CLOSING PHASE (Interactive) ==========
        print("\n[CLOSING PHASE]")

        # Interactive closing: continue until closing_complete flag is set
        closing_turn = 0
        max_closing_turns = 5  # Safety limit
        while closing_turn < max_closing_turns:
            state = await get_session_state(session_service, test_session)
            if state.get("closing_complete"):
                print("✓ Closing complete")
                break

            interviewer_msg = await get_last_agent_message(session_service, test_session)
            print(f"  Turn {closing_turn + 1} Interviewer: {interviewer_msg[:80]}...")

            # Generate appropriate candidate response
            if closing_turn == 0:
                # First turn: Ask questions or say no questions
                phase_hint = "closing_question"
            else:
                # Subsequent turns: Thanks/goodbye
                phase_hint = "closing_thanks"

            candidate_msg = await candidate.generate_response(
                interviewer_msg, phase_hint, candidate_profile
            )
            await send_message(runner, test_session, candidate_msg)
            total_interviewer_calls += 1
            print(f"  Turn {closing_turn + 1} Candidate: {candidate_msg[:80]}...")

            closing_turn += 1

        # ========== VERIFY COMPLETION ==========
        state = await get_session_state(session_service, test_session)
        assert state.get("interview_phases_complete") is True
        assert state.get("closing_complete") is True
        assert state.get("interview_phase") == "done"

        # ========== REPORT LLM CALLS ==========
        print("\n" + "=" * 80)
        print("TEST COMPLETE")
        print("=" * 80)
        print(f"Total Interviewer LLM Calls: {total_interviewer_calls}")
        print(f"Total Candidate LLM Calls: {candidate.llm_call_count}")
        print(f"Total LLM Calls: {total_interviewer_calls + candidate.llm_call_count}")
        print(f"Phases Completed: {state.get('current_phase_idx')}")
        print("=" * 80)

    @pytest.mark.asyncio
    @pytest.mark.timeout(600)
    async def test_e2e_interview_paid_remote(
        self, runner, session_service, test_session, mock_google_agent
    ):
        """
        Complete E2E test with PAID REMOTE agent (Google) using LLM-generated responses.

        Flow:
        1. Routing: User states preference for Google
        2. Intro: Multi-turn conversation collecting candidate info
        3. Design: Multi-turn conversations for each phase (3 phases total)
           (plan_and_scope, requirements_alignment, architecture_blueprint)
        4. Closing: Thank you, questions, and goodbye
        5. All responses generated by LLM to simulate real candidate

        Expected LLM calls: ~20-25 (interviewer + candidate)
        Time: ~2-3 minutes
        """
        candidate = CandidateResponseGenerator()
        candidate_profile = {
            "name": "Sarah Johnson",
            "years_experience": 8,
            "domain": "backend distributed systems",
        }

        total_interviewer_calls = 0
        print("\n" + "=" * 80)
        print("E2E TEST: Paid Remote Agent (Google)")
        print("=" * 80)

        # ========== ROUTING PHASE ==========
        print("\n[ROUTING PHASE]")

        await send_message(runner, test_session, "Hello!")
        total_interviewer_calls += 1
        interviewer_msg = await get_last_agent_message(session_service, test_session)
        print(f"Interviewer: {interviewer_msg[:100]}...")

        # Candidate requests Google system design
        candidate_msg = "I want to do a Google system design interview"
        await send_message(runner, test_session, candidate_msg)
        total_interviewer_calls += 1
        print(f"Candidate: {candidate_msg}")

        state = await get_session_state(session_service, test_session)
        assert "routing_decision" in state
        assert state["routing_decision"]["company"] == "google"
        print("✓ Routing complete")

        # ========== INTRO PHASE (Multi-turn) ==========
        print("\n[INTRO PHASE]")

        # Turn 1: Name and experience
        interviewer_msg = await get_last_agent_message(session_service, test_session)
        print(f"Interviewer: {interviewer_msg[:100]}...")

        candidate_msg = await candidate.generate_response(
            interviewer_msg, "intro_name", candidate_profile
        )
        await send_message(runner, test_session, candidate_msg)
        total_interviewer_calls += 1
        print(f"Candidate: {candidate_msg}")

        # Turn 2: Domain expertise
        interviewer_msg = await get_last_agent_message(session_service, test_session)
        print(f"Interviewer: {interviewer_msg[:100]}...")

        candidate_msg = await candidate.generate_response(
            interviewer_msg, "intro_domain", candidate_profile
        )
        await send_message(runner, test_session, candidate_msg)
        total_interviewer_calls += 1
        print(f"Candidate: {candidate_msg}")

        state = await get_session_state(session_service, test_session)
        assert "candidate_info" in state
        assert state.get("interview_phase") == "design"
        print("✓ Intro complete, moving to design")

        # ========== DESIGN PHASE (Multi-turn per phase) ==========
        print("\n[DESIGN PHASE]")

        # Phase 0: plan_and_scope (2-3 turns)
        print("\n[Phase 0: plan_and_scope]")
        for turn in range(3):
            interviewer_msg = await get_last_agent_message(session_service, test_session)
            print(f"  Turn {turn + 1} Interviewer: {interviewer_msg[:80]}...")

            candidate_msg = await candidate.generate_response(
                interviewer_msg, "plan_and_scope", candidate_profile
            )
            await send_message(runner, test_session, candidate_msg)
            total_interviewer_calls += 1
            print(f"  Turn {turn + 1} Candidate: {candidate_msg[:80]}...")

            state = await get_session_state(session_service, test_session)
            if state.get("current_phase_idx", 0) > 0:
                print("  ✓ Phase 0 complete")
                break

        # Phase 1: requirements_alignment (2 turns)
        print("\n[Phase 1: requirements_alignment]")
        for turn in range(2):
            interviewer_msg = await get_last_agent_message(session_service, test_session)
            print(f"  Turn {turn + 1} Interviewer: {interviewer_msg[:80]}...")

            candidate_msg = await candidate.generate_response(
                interviewer_msg, "requirements_alignment", candidate_profile
            )
            await send_message(runner, test_session, candidate_msg)
            total_interviewer_calls += 1
            print(f"  Turn {turn + 1} Candidate: {candidate_msg[:80]}...")

            state = await get_session_state(session_service, test_session)
            if state.get("current_phase_idx", 0) > 1:
                print("  ✓ Phase 1 complete")
                break

        # Phase 2: architecture_blueprint (2 turns)
        print("\n[Phase 2: architecture_blueprint]")
        for turn in range(2):
            interviewer_msg = await get_last_agent_message(session_service, test_session)
            print(f"  Turn {turn + 1} Interviewer: {interviewer_msg[:80]}...")

            candidate_msg = await candidate.generate_response(
                interviewer_msg, "architecture_blueprint", candidate_profile
            )
            await send_message(runner, test_session, candidate_msg)
            total_interviewer_calls += 1
            print(f"  Turn {turn + 1} Candidate: {candidate_msg[:80]}...")

            state = await get_session_state(session_service, test_session)
            if state.get("current_phase_idx", 0) > 2:
                print("  ✓ Phase 2 complete")
                break

        # ========== CLOSING PHASE (Interactive) ==========
        print("\n[CLOSING PHASE]")

        # Interactive closing: continue until closing_complete flag is set
        closing_turn = 0
        max_closing_turns = 5  # Safety limit
        while closing_turn < max_closing_turns:
            state = await get_session_state(session_service, test_session)
            if state.get("closing_complete"):
                print("✓ Closing complete")
                break

            interviewer_msg = await get_last_agent_message(session_service, test_session)
            print(f"  Turn {closing_turn + 1} Interviewer: {interviewer_msg[:80]}...")

            # Generate appropriate candidate response
            if closing_turn == 0:
                # First turn: Ask questions or say no questions
                phase_hint = "closing_question"
            else:
                # Subsequent turns: Thanks/goodbye
                phase_hint = "closing_thanks"

            candidate_msg = await candidate.generate_response(
                interviewer_msg, phase_hint, candidate_profile
            )
            await send_message(runner, test_session, candidate_msg)
            total_interviewer_calls += 1
            print(f"  Turn {closing_turn + 1} Candidate: {candidate_msg[:80]}...")

            closing_turn += 1

        # ========== VERIFY COMPLETION ==========
        state = await get_session_state(session_service, test_session)
        assert state.get("interview_phases_complete") is True
        assert state.get("closing_complete") is True
        assert state.get("interview_phase") == "done"

        # ========== REPORT LLM CALLS ==========
        print("\n" + "=" * 80)
        print("TEST COMPLETE")
        print("=" * 80)
        print(f"Total Interviewer LLM Calls: {total_interviewer_calls}")
        print(f"Total Candidate LLM Calls: {candidate.llm_call_count}")
        print(f"Total LLM Calls: {total_interviewer_calls + candidate.llm_call_count}")
        print(f"Phases Completed: {state.get('current_phase_idx')}")
        print("=" * 80)
