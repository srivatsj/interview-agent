"""Unit tests for coding interview agent tools."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from ap2.types.payment_receipt import PAYMENT_RECEIPT_DATA_KEY

from interview_orchestrator.agents.interview_types.coding import ask_remote_expert


@pytest.mark.asyncio
class TestAskRemoteExpertCoding:
    """Test ask_remote_expert tool (coding variant)."""

    @patch("interview_orchestrator.agents.interview_types.coding.call_remote_skill")
    @patch(
        "interview_orchestrator.agents.interview_types.coding.AgentProviderRegistry.get_agent_url"
    )
    async def test_includes_payment_receipt_when_available(self, mock_get_url, mock_remote_call):
        """Test that payment receipt is always included when available."""
        mock_get_url.return_value = "http://localhost:8001"
        mock_remote_call.return_value = {"message": "Good implementation!"}

        tool_context = MagicMock()
        tool_context.state = {
            "routing_decision": {"company": "google", "interview_type": "coding"},
            "interview_id": "test_456",
            "user_id": "test_user",
            "payment_proof": {"payment_id": "test_payment_456"},
        }

        result = await ask_remote_expert(query="Here's my solution", tool_context=tool_context)

        assert result == "Good implementation!"

        # Check payment receipt was included
        call_args = mock_remote_call.call_args
        assert call_args[1]["data"][PAYMENT_RECEIPT_DATA_KEY] == {"payment_id": "test_payment_456"}

    @patch("interview_orchestrator.agents.interview_types.coding.call_remote_skill")
    @patch(
        "interview_orchestrator.agents.interview_types.coding.AgentProviderRegistry.get_agent_url"
    )
    async def test_canvas_screenshot_included(self, mock_get_url, mock_remote_call):
        """Test that canvas screenshot is included when available."""
        mock_get_url.return_value = "http://localhost:8001"
        mock_remote_call.return_value = {"message": "Nice code structure"}

        tool_context = MagicMock()
        tool_context.state = {
            "routing_decision": {"company": "google", "interview_type": "coding"},
            "interview_id": "test_456",
            "user_id": "test_user",
            "canvas_screenshot": "base64_canvas_image_data",
        }

        result = await ask_remote_expert(query="What do you think?", tool_context=tool_context)

        assert result == "Nice code structure"

        # Check canvas screenshot was included
        call_args = mock_remote_call.call_args
        assert call_args[1]["data"]["canvas_screenshot"] == "base64_canvas_image_data"
