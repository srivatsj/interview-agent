"""Unit tests for closing tools."""

from unittest.mock import MagicMock

from interview_orchestrator.shared.tools.closing_tools import mark_interview_complete


def test_mark_interview_complete():
    """Test interview complete tool marks interview as done."""
    tool_context = MagicMock()
    tool_context.state = {"interview_phase": "closing"}

    result = mark_interview_complete(tool_context=tool_context)

    # Verify state
    assert tool_context.state["interview_complete"] is True
    assert tool_context.state["interview_phase"] == "done"

    # Verify result message
    assert "complete" in result.lower()


def test_mark_interview_complete_empty_state():
    """Test interview complete works with empty state."""
    tool_context = MagicMock()
    tool_context.state = {}

    mark_interview_complete(tool_context=tool_context)

    assert tool_context.state["interview_complete"] is True
    assert tool_context.state["interview_phase"] == "done"
