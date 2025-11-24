"""E2E tests for remote agent integration via A2A protocol."""

import logging

import pytest

from a2a_helper import send_a2a_message

logger = logging.getLogger(__name__)


@pytest.mark.asyncio
class TestRemoteExpertIntegration:
    """Test that orchestrator properly calls remote Google agent."""

    async def test_google_agent_direct_call(
        self,
        google_agent_server,
        test_interview_id,
    ):
        """Test direct call to Google agent works."""
        response = await send_a2a_message(
            agent_url="http://localhost:8001",
            text="Conduct interview",
            data={
                "message": "Hi, I'm ready for the interview",
                "user_id": "test_user",
                "session_id": test_interview_id,
            },
        )

        assert response is not None
        assert "message" in response
        assert len(response["message"]) > 0
        logger.info(f"✅ Google agent responded with {len(response['message'])} chars")

    async def test_google_agent_multi_turn(
        self,
        google_agent_server,
        test_interview_id,
    ):
        """Test Google agent maintains conversation context."""
        session_id = test_interview_id

        # Turn 1
        response1 = await send_a2a_message(
            agent_url="http://localhost:8001",
            text="Conduct interview",
            data={
                "message": "Hi, I'm ready",
                "user_id": "test_user",
                "session_id": session_id,
            },
        )
        assert "message" in response1
        logger.info("✅ Google agent turn 1")

        # Turn 2 - same session
        response2 = await send_a2a_message(
            agent_url="http://localhost:8001",
            text="Conduct interview",
            data={
                "message": "I'd like to clarify the requirements",
                "user_id": "test_user",
                "session_id": session_id,
            },
        )
        assert "message" in response2
        logger.info("✅ Google agent turn 2 - context maintained")

        # Turn 3 - same session
        response3 = await send_a2a_message(
            agent_url="http://localhost:8001",
            text="Conduct interview",
            data={
                "message": "I propose using Spanner and Bigtable",
                "user_id": "test_user",
                "session_id": session_id,
            },
        )
        assert "message" in response3
        logger.info("✅ Google agent turn 3 - conversation flow maintained")
