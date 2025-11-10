"""Unit tests for design agent tool."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from interview_orchestrator.interview_types.system_design.design_agent_tool import (
    initialize_design_phase,
    mark_design_complete,
)


@pytest.mark.asyncio
async def test_initialize_design_phase_with_default():
    """Test initializing design phase with default company (local provider)."""
    tool_context = MagicMock()
    tool_context.state = {
        "routing_decision": {"company": "default", "interview_type": "system_design"},
        "candidate_info": {"name": "Alice", "years_experience": 5},
    }

    # Mock the provider
    mock_provider = AsyncMock()
    mock_provider.start_interview.return_value = {"status": "ok"}
    mock_provider.get_question.return_value = "Design a URL shortening service"

    with patch(
        "interview_orchestrator.interview_types.system_design.design_agent_tool.CompanyFactory.get_tools",
        return_value=mock_provider,
    ):
        result = await initialize_design_phase(tool_context=tool_context)

        # Verify provider was called
        mock_provider.start_interview.assert_called_once_with(
            "system_design", {"name": "Alice", "years_experience": 5}
        )
        mock_provider.get_question.assert_called_once()

        # Verify state
        assert tool_context.state["interview_question"] == "Design a URL shortening service"

        # Verify result
        assert "Design a URL shortening service" in result


@pytest.mark.asyncio
async def test_initialize_design_phase_stores_question():
    """Test design phase stores full question in state."""
    tool_context = MagicMock()
    tool_context.state = {
        "routing_decision": {"company": "default", "interview_type": "system_design"},
        "candidate_info": {},
    }

    mock_provider = AsyncMock()
    mock_provider.start_interview.return_value = {"status": "ok"}
    mock_provider.get_question.return_value = (
        "Design a highly scalable distributed cache system like Redis"
    )

    with patch(
        "interview_orchestrator.interview_types.system_design.design_agent_tool.CompanyFactory.get_tools",
        return_value=mock_provider,
    ):
        await initialize_design_phase(tool_context=tool_context)

        # Full question stored
        assert (
            tool_context.state["interview_question"]
            == "Design a highly scalable distributed cache system like Redis"
        )


def test_mark_design_complete():
    """Test marking design phase as complete."""
    tool_context = MagicMock()
    tool_context.state = {"interview_phase": "design"}

    result = mark_design_complete(tool_context=tool_context)

    # Verify state
    assert tool_context.state["design_complete"] is True
    assert tool_context.state["interview_phase"] == "closing"

    # Verify result message
    assert "complete" in result.lower()
    assert "closing" in result.lower()


def test_mark_design_complete_empty_state():
    """Test design complete works with empty state."""
    tool_context = MagicMock()
    tool_context.state = {}

    mark_design_complete(tool_context=tool_context)

    assert tool_context.state["design_complete"] is True
    assert tool_context.state["interview_phase"] == "closing"
