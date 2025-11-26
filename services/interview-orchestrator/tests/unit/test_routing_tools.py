"""Unit tests for routing agent tools."""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from interview_orchestrator.agents.routing import confirm_company_selection


@pytest.mark.asyncio
class TestConfirmCompanySelection:
    """Test confirm_company_selection tool."""

    @patch.dict(os.environ, {"ENV": "test", "AUTO_APPROVE_PAYMENTS": "true"})
    @patch("interview_orchestrator.agents.routing.get_cart_mandate")
    @patch("interview_orchestrator.agents.routing.AgentProviderRegistry.is_valid_combination")
    @patch("interview_orchestrator.agents.routing.AgentProviderRegistry.get_agent_url")
    async def test_auto_approve_in_test_mode(self, mock_get_url, mock_is_valid, mock_get_cart):
        """Test auto-approve payment in test mode."""
        # Setup mocks
        mock_is_valid.return_value = True
        mock_get_url.return_value = "http://localhost:8001"
        mock_get_cart.return_value = (
            {"contents": {"payment_request": {"details": {"total": {"amount": {"value": 3.0}}}}}},
            None,
        )

        # Create mock tool context
        tool_context = MagicMock()
        tool_context.state = {}

        # Call tool
        result = await confirm_company_selection(
            company="google", interview_type="system_design", tool_context=tool_context
        )

        # Assertions
        assert "PAYMENT_SUCCESS" in result
        assert tool_context.state["payment_completed"] is True
        assert "payment_proof" in tool_context.state
        assert tool_context.state["payment_proof"]["payment_id"].startswith("test_auto_approve_")
        assert tool_context.state["routing_decision"]["company"] == "google"
        assert tool_context.state["interview_phase"] == "intro"

    @patch("interview_orchestrator.agents.routing.AgentProviderRegistry.is_valid_combination")
    async def test_invalid_company_combination(self, mock_is_valid):
        """Test error handling for invalid company/interview_type."""
        mock_is_valid.return_value = False

        tool_context = MagicMock()
        tool_context.state = {}

        result = await confirm_company_selection(
            company="invalid", interview_type="system_design", tool_context=tool_context
        )

        assert "Error" in result
        assert "not available" in result

    @patch("interview_orchestrator.agents.routing.AgentProviderRegistry.is_valid_combination")
    async def test_duplicate_payment_attempt(self, mock_is_valid):
        """Test that duplicate payment attempts are prevented."""
        mock_is_valid.return_value = True

        tool_context = MagicMock()
        tool_context.state = {"payment_completed": True}

        result = await confirm_company_selection(
            company="google", interview_type="system_design", tool_context=tool_context
        )

        assert "INTERNAL" in result
        assert "already completed" in result
