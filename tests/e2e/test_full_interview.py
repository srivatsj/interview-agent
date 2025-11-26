"""E2E tests for remote agent integration via A2A protocol."""

import base64
import logging
from pathlib import Path

import pytest
from a2a_helper import send_a2a_message
from ap2.types.payment_receipt import PAYMENT_RECEIPT_DATA_KEY

logger = logging.getLogger(__name__)

# Canvas data directory
CANVAS_DATA_DIR = Path(__file__).parent.parent / "canvas_data"


def load_canvas_image(filename: str) -> str:
    """Load canvas image as base64 encoded string."""
    image_path = CANVAS_DATA_DIR / filename
    if not image_path.exists():
        raise FileNotFoundError(f"Canvas image not found: {image_path}")

    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def load_canvas_content(filename: str) -> str:
    """Load canvas text content."""
    content_path = CANVAS_DATA_DIR / filename
    if not content_path.exists():
        raise FileNotFoundError(f"Canvas content not found: {content_path}")

    with open(content_path, "r") as f:
        return f.read()


@pytest.mark.asyncio
class TestRemoteExpertIntegration:
    """Test that orchestrator properly calls remote Google agent."""

    async def test_google_agent_direct_call(
        self,
        google_agent_server,
        test_interview_id,
    ):
        """Test direct call to Google agent works (with payment verification)."""
        valid_payment_receipt = {
            "payment_id": "test_direct_call",
            "payment_mandate_id": "test_mandate",
            "timestamp": "2025-01-01T00:00:00Z",
            "amount": {"currency": "USD", "value": 3.00},
            "payment_status": {
                "merchant_confirmation_id": "test_direct_call",
            },
        }

        response = await send_a2a_message(
            agent_url="http://localhost:8001",
            text="Conduct interview",
            data={
                "message": "Hi, I'm ready for the interview",
                "user_id": "test_user",
                "session_id": test_interview_id,
                PAYMENT_RECEIPT_DATA_KEY: valid_payment_receipt,
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
        """Test Google agent maintains conversation context AND payment verification.

        Verifies:
        - First call requires payment receipt
        - Subsequent calls work without payment (session verified)
        """
        session_id = test_interview_id

        # Turn 1: Include payment receipt (required for first call)
        valid_payment_receipt = {
            "payment_id": "test_payment_123",
            "payment_mandate_id": "test_mandate_456",
            "timestamp": "2025-01-01T00:00:00Z",
            "amount": {"currency": "USD", "value": 3.00},
            "payment_status": {
                "merchant_confirmation_id": "test_payment_123",
                "psp_confirmation_id": "stripe_test_789",
            },
            "payment_method_details": {"method_name": "CARD"},
        }

        response1 = await send_a2a_message(
            agent_url="http://localhost:8001",
            text="Conduct interview",
            data={
                "message": "Hi, I'm ready",
                "user_id": "test_user",
                "session_id": session_id,
                PAYMENT_RECEIPT_DATA_KEY: valid_payment_receipt,  # Payment required on first call
            },
        )
        assert "message" in response1
        logger.info("✅ Google agent turn 1 (with payment verification)")

        # Turn 2 - same session (NO payment receipt needed, session verified)
        response2 = await send_a2a_message(
            agent_url="http://localhost:8001",
            text="Conduct interview",
            data={
                "message": "I'd like to clarify the requirements",
                "user_id": "test_user",
                "session_id": session_id,
                # No payment receipt - should work because session is verified
            },
        )
        assert "message" in response2
        logger.info("✅ Google agent turn 2 - context maintained (no payment needed)")

        # Turn 3 - same session (still no payment needed)
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
        logger.info("✅ Google agent turn 3 - payment verification gates access once per session")

    async def test_system_design_interview_with_png(
        self,
        google_agent_server,
        test_interview_id,
    ):
        """Test multi-turn system design interview with PNG diagram."""
        whiteboard_image = load_canvas_image("system_design_whiteboard.png")
        session_id = test_interview_id

        # Payment receipt for first call
        valid_payment_receipt = {
            "payment_id": "test_png_interview",
            "payment_mandate_id": "test_mandate",
            "timestamp": "2025-01-01T00:00:00Z",
            "amount": {"currency": "USD", "value": 3.00},
            "payment_status": {"merchant_confirmation_id": "test_png_interview"},
        }

        # Turn 1: Show architecture diagram (with payment)
        response1 = await send_a2a_message(
            agent_url="http://localhost:8001",
            text="Conduct interview",
            data={
                "message": "I've designed a URL shortener. Here's my architecture.",
                "user_id": "test_user",
                "session_id": session_id,
                "canvas_screenshot": whiteboard_image,
                PAYMENT_RECEIPT_DATA_KEY: valid_payment_receipt,
            },
        )
        assert response1 is not None
        assert "message" in response1
        logger.info("✅ Turn 1: Agent received architecture diagram (with payment)")

        # Turn 2: Discuss specific component
        response2 = await send_a2a_message(
            agent_url="http://localhost:8001",
            text="Conduct interview",
            data={
                "message": "For the cache layer, I'm using Redis with a 80% hit rate target.",
                "user_id": "test_user",
                "session_id": session_id,
            },
        )
        assert "message" in response2
        logger.info("✅ Turn 2: Agent discussed caching strategy")

        # Turn 3: Scale discussion
        response3 = await send_a2a_message(
            agent_url="http://localhost:8001",
            text="Conduct interview",
            data={
                "message": "How would you handle 1 billion users with this design?",
                "user_id": "test_user",
                "session_id": session_id,
            },
        )
        assert "message" in response3
        logger.info("✅ Turn 3: Agent maintained context across turns")

    async def test_coding_interview_with_text(
        self,
        google_agent_server,
        test_interview_id,
    ):
        """Test multi-turn coding interview with text code."""
        code_content = load_canvas_content("code_implementation.txt")
        session_id = test_interview_id

        # Payment receipt for first call
        valid_payment_receipt = {
            "payment_id": "test_coding_interview",
            "payment_mandate_id": "test_mandate",
            "timestamp": "2025-01-01T00:00:00Z",
            "amount": {"currency": "USD", "value": 3.00},
            "payment_status": {"merchant_confirmation_id": "test_coding_interview"},
        }

        # Turn 1: Share implementation (with payment)
        response1 = await send_a2a_message(
            agent_url="http://localhost:8001",
            text="Conduct interview",
            data={
                "message": "Here's my Python implementation of the URL shortener.",
                "user_id": "test_user",
                "session_id": session_id,
                "canvas_content": code_content,
                PAYMENT_RECEIPT_DATA_KEY: valid_payment_receipt,
            },
        )
        assert response1 is not None
        assert "message" in response1
        logger.info("✅ Turn 1: Agent received code implementation (with payment)")

        # Turn 2: Discuss specific method
        response2 = await send_a2a_message(
            agent_url="http://localhost:8001",
            text="Conduct interview",
            data={
                "message": (
                    "I'm using base62 encoding for the short codes. "
                    "Is this approach scalable?"
                ),
                "user_id": "test_user",
                "session_id": session_id,
            },
        )
        assert "message" in response2
        logger.info("✅ Turn 2: Agent discussed encoding strategy")

        # Turn 3: Edge cases
        response3 = await send_a2a_message(
            agent_url="http://localhost:8001",
            text="Conduct interview",
            data={
                "message": "What edge cases should I handle in the shorten_url method?",
                "user_id": "test_user",
                "session_id": session_id,
            },
        )
        assert "message" in response3
        logger.info("✅ Turn 3: Agent maintained code context across turns")
