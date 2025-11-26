"""Unit tests for design interview agent tools."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from ap2.types.payment_receipt import PAYMENT_RECEIPT_DATA_KEY

from interview_orchestrator.agents.interview_types.design import ask_remote_expert


@pytest.mark.asyncio
class TestAskRemoteExpert:
    """Test ask_remote_expert tool."""

    @patch("interview_orchestrator.agents.interview_types.design.call_remote_skill")
    @patch(
        "interview_orchestrator.agents.interview_types.design.AgentProviderRegistry.get_agent_url"
    )
    async def test_includes_payment_receipt_when_available(self, mock_get_url, mock_remote_call):
        """Test that payment receipt is always included when available."""
        # Setup mocks
        mock_get_url.return_value = "http://localhost:8001"
        mock_remote_call.return_value = {"message": "Great design!"}

        # Create mock tool context
        tool_context = MagicMock()
        tool_context.state = {
            "routing_decision": {"company": "google", "interview_type": "system_design"},
            "interview_id": "test_123",
            "user_id": "test_user",
            "payment_proof": {"payment_id": "test_payment_123"},
        }

        # Call tool
        result = await ask_remote_expert(query="Here's my architecture", tool_context=tool_context)

        # Assertions
        assert result == "Great design!"

        # Check payment receipt was included
        call_args = mock_remote_call.call_args
        assert call_args[1]["data"][PAYMENT_RECEIPT_DATA_KEY] == {"payment_id": "test_payment_123"}

    @patch("interview_orchestrator.agents.interview_types.design.call_remote_skill")
    @patch(
        "interview_orchestrator.agents.interview_types.design.AgentProviderRegistry.get_agent_url"
    )
    async def test_multiple_calls_always_include_payment_receipt(
        self, mock_get_url, mock_remote_call
    ):
        """Test that payment receipt is included on every call."""
        mock_get_url.return_value = "http://localhost:8001"
        mock_remote_call.return_value = {"message": "Good scaling approach"}

        tool_context = MagicMock()
        tool_context.state = {
            "routing_decision": {"company": "google", "interview_type": "system_design"},
            "interview_id": "test_123",
            "user_id": "test_user",
            "payment_proof": {"payment_id": "test_payment_123"},
        }

        # Make multiple calls
        await ask_remote_expert(query="First question", tool_context=tool_context)
        result = await ask_remote_expert(
            query="How should I scale this?", tool_context=tool_context
        )

        assert result == "Good scaling approach"

        # Check payment receipt was included in second call too
        call_args = mock_remote_call.call_args
        assert call_args[1]["data"][PAYMENT_RECEIPT_DATA_KEY] == {"payment_id": "test_payment_123"}

    @patch("interview_orchestrator.agents.interview_types.design.call_remote_skill")
    @patch(
        "interview_orchestrator.agents.interview_types.design.AgentProviderRegistry.get_agent_url"
    )
    async def test_canvas_screenshot_included(self, mock_get_url, mock_remote_call):
        """Test that canvas screenshot is included when available."""
        mock_get_url.return_value = "http://localhost:8001"
        mock_remote_call.return_value = {"message": "Nice diagram"}

        tool_context = MagicMock()
        tool_context.state = {
            "routing_decision": {"company": "google", "interview_type": "system_design"},
            "interview_id": "test_123",
            "user_id": "test_user",
            "canvas_screenshot": "base64_image_data",
        }

        result = await ask_remote_expert(query="What do you think?", tool_context=tool_context)

        assert result == "Nice diagram"

        # Check canvas was included
        call_args = mock_remote_call.call_args
        assert call_args[1]["data"]["canvas_screenshot"] == "base64_image_data"
