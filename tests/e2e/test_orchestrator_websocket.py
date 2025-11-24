"""E2E tests for orchestrator via WebSocket (simulating frontend)."""

import logging

import pytest

from websocket_helper import WebSocketTestClient

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
@pytest.mark.e2e
class TestOrchestratorWebSocket:
    """Test orchestrator via WebSocket - simulates frontend communication."""

    async def test_websocket_connection(
        self,
        orchestrator_server,
        google_agent_server,
        test_user_id,
        test_interview_id,
    ):
        """Test basic WebSocket connection to orchestrator."""
        client = WebSocketTestClient(test_user_id, test_interview_id)

        try:
            await client.connect()
            logger.info("✅ WebSocket connected successfully")

            # Send simple greeting
            responses = await client.send_and_wait("Hello", wait_for_complete=True)

            # Verify we got responses
            assert len(responses) > 0, "Expected at least one response"

            # Extract text responses
            text_content = client.get_text_responses()
            assert len(text_content) > 0, "Expected non-empty text response"

            logger.info(f"✅ Received response: {text_content[:100]}...")

        finally:
            await client.close()

    async def test_routing_phase(
        self,
        orchestrator_server,
        google_agent_server,
        test_user_id,
        test_interview_id,
    ):
        """Test routing phase - selecting interview type."""
        client = WebSocketTestClient(test_user_id, test_interview_id)

        try:
            await client.connect()

            # Initial greeting - should be in routing phase
            await client.send_and_wait("Hello, I want to practice interviews")
            logger.info("✅ Sent greeting in routing phase")

            # Select interview type
            await client.send_and_wait(
                "I'd like to do a Google system design interview"
            )

            # Verify we got text responses
            text_content = client.get_text_responses()
            logger.info(f"📋 Received {len(text_content)} chars of text")

            # Should receive text responses from routing agent
            assert len(text_content) > 0, "Expected text response from routing phase"

            logger.info("✅ Routing phase completed")

        finally:
            await client.close()

    async def test_end_to_end_simple_flow(
        self,
        orchestrator_server,
        google_agent_server,
        test_user_id,
        test_interview_id,
    ):
        """Test simple end-to-end flow through orchestrator to Google agent."""
        client = WebSocketTestClient(test_user_id, test_interview_id)

        try:
            await client.connect()
            logger.info("✅ Connected to orchestrator")

            # Turn 1: Greeting
            await client.send_and_wait("Hello")
            logger.info("✅ Turn 1: Greeting sent")

            # Turn 2: Select interview type
            await client.send_and_wait("Google system design interview")
            logger.info("✅ Turn 2: Selected interview type")

            # Turn 3: Start interview (if not blocked by payment)
            # Note: With AUTO_APPROVE_PAYMENTS=true, this should work
            await client.send_and_wait("I'm ready to start the interview")

            # Verify we got responses
            text_content = client.get_text_responses()
            logger.info(f"✅ Turn 3: Got {len(text_content)} chars of response")

            # At this point, orchestrator should have called Google agent via A2A
            # and we should see interview-style responses
            assert len(text_content) > 50, "Expected substantial interview response"

            logger.info("✅ End-to-end flow completed")

        finally:
            await client.close()


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.slow
class TestOrchestratorPhaseTransitions:
    """Test phase transitions (requires full implementation)."""

    async def test_full_phase_flow(
        self,
        orchestrator_server,
        google_agent_server,
        test_user_id,
        test_interview_id,
    ):
        """Test complete phase flow: routing → intro → interview → closing → done.

        Note: This test may need adjustments based on orchestrator phase logic.
        """
        pytest.skip("Not fully implemented - needs phase transition logic verification")

        # Implementation outline:
        # 1. Connect via WebSocket
        # 2. Routing: Select interview type
        # 3. Payment: Auto-approved in test mode
        # 4. Intro: Agent introduces interview
        # 5. Interview: Multiple turns with Google agent
        # 6. Closing: Wrap up and get feedback
        # 7. Done: Session complete
        #
        # At each step, verify phase in database and message types
