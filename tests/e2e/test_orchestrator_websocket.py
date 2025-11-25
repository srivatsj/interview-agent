"""E2E tests for orchestrator via WebSocket (simulating frontend)."""

import base64
import logging
from pathlib import Path

import pytest
from websocket_helper import WebSocketTestClient

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
@pytest.mark.e2e
class TestOrchestratorCriticalUserJourneys:
    """Test critical user journeys with state, phase, and payment verification."""

    async def test_phase_transitions_routing_to_design(
        self,
        orchestrator_server,
        google_agent_server,
        test_user_id,
        test_interview_id,
        get_session,
    ):
        """Test phase transitions: routing → payment → intro → design.

        Verifies state, payment completion, candidate info collection, and phase transitions.
        Does not test design phase functionality itself.
        """
        client = WebSocketTestClient(test_user_id, test_interview_id)

        try:
            await client.connect()

            # Phase 1: Routing
            await client.send_and_wait("Hello, I want to practice interviews")
            session = get_session(test_user_id, test_interview_id)
            assert session["state"]["interview_phase"] == "routing"

            # Phase 2: Payment (auto-approved in test mode)
            await client.send_and_wait("I'd like a Google system design interview")
            session = get_session(test_user_id, test_interview_id)
            assert session["state"]["interview_phase"] == "intro"
            assert session["state"]["payment_completed"] is True
            assert session["state"]["routing_decision"]["company"] == "google"

            # Verify payment tool was called
            tool_names = [tc["name"] for tc in session["tool_calls"]]
            assert "confirm_company_selection" in tool_names

            # Phase 3: Intro → Interview (collect candidate info via multi-turn conversation)
            await client.send_and_wait("My name is John")
            await client.send_and_wait("I have 5 years of experience")
            await client.send_and_wait("I work in distributed systems")
            await client.send_and_wait(
                "I've built URL shorteners and caching systems", wait_for_complete=True
            )

            session = get_session(test_user_id, test_interview_id)

            # Debug: Print session state
            logger.info(f"🔍 Session state: {session['state']}")
            logger.info(f"🔍 Tool calls found: {[tc['name'] for tc in session['tool_calls']]}")
            logger.info(f"🔍 Total tool calls: {len(session['tool_calls'])}")

            assert session["state"]["interview_phase"] == "interview", (
                f"Expected 'interview' but got '{session['state'].get('interview_phase')}'"
            )
            assert session["state"]["candidate_info"]["name"] == "John"
            assert session["state"]["candidate_info"]["years_experience"] == 5

            # Verify candidate info tool was called
            tool_names = [tc["name"] for tc in session["tool_calls"]]
            assert "save_candidate_info" in tool_names, f"save_candidate_info not in {tool_names}"

            logger.info("✅ Phase transitions verified: routing → payment → intro → design")

        finally:
            await client.close()

    async def test_full_e2e_with_design_and_closing(
        self,
        orchestrator_server,
        google_agent_server,
        test_user_id,
        test_interview_id,
        get_session,
    ):
        """Full E2E journey: routing → payment → intro → design (with canvas) → closing.

        Tests complete interview flow including canvas PNG handling and closing phase.
        """
        client = WebSocketTestClient(test_user_id, test_interview_id)
        canvas_dir = Path(__file__).parent.parent / "canvas_data"
        with open(canvas_dir / "system_design_whiteboard.png", "rb") as f:
            canvas_b64 = base64.b64encode(f.read()).decode("utf-8")

        try:
            await client.connect()

            # Phase 1: Routing → Payment
            await client.send_and_wait("Hello, I want to practice interviews")
            await client.send_and_wait("I'd like a Google system design interview")
            session = get_session(test_user_id, test_interview_id)
            assert session["state"]["interview_phase"] == "intro"
            assert session["state"]["payment_completed"] is True

            # Phase 2: Intro → Interview (collect candidate info via multi-turn conversation)
            await client.send_and_wait("My name is John")
            await client.send_and_wait("I have 5 years of experience")
            await client.send_and_wait("I work in distributed systems")
            await client.send_and_wait(
                "I've built URL shorteners and caching systems", wait_for_complete=True
            )

            session = get_session(test_user_id, test_interview_id)
            assert session["state"]["interview_phase"] == "interview"
            assert session["state"]["candidate_info"]["years_experience"] == 5

            # Phase 3: Design - Turn 1 with canvas PNG
            client.messages.clear()
            await client.send_canvas_image(canvas_b64)
            await client.send_and_wait(
                "Here's my URL shortener architecture. What do you think?", timeout=45.0
            )

            session = get_session(test_user_id, test_interview_id)
            assert session["state"]["canvas_screenshot"] == canvas_b64
            text1 = client.get_text_responses()
            assert len(text1) > 0

            # Phase 3: Design - Turn 2 (verify context and canvas persistence)
            client.messages.clear()
            await client.send_and_wait(
                "For the database, I'm thinking PostgreSQL with sharding.", timeout=45.0
            )

            session = get_session(test_user_id, test_interview_id)
            assert session["state"]["canvas_screenshot"] == canvas_b64  # Canvas persisted
            text2 = client.get_text_responses()
            assert len(text2) > 0

            # Phase 4: Closing
            client.messages.clear()
            await client.send_and_wait("I think I'm done with my design", timeout=30.0)

            # Verify all critical tools were called
            session = get_session(test_user_id, test_interview_id)
            tool_names = [tc["name"] for tc in session["tool_calls"]]
            assert "confirm_company_selection" in tool_names
            assert "save_candidate_info" in tool_names

            logger.info(
                "✅ Full E2E verified: routing → payment → intro → design (canvas) → closing"
            )

        finally:
            await client.close()
