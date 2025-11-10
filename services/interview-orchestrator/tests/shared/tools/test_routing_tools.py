"""Unit tests for routing tools."""

from unittest.mock import MagicMock

from interview_orchestrator.shared.tools.routing_tools import set_routing_decision


def test_set_routing_decision():
    """Test routing decision tool saves decision and transitions to intro."""
    # Create mock context
    tool_context = MagicMock()
    tool_context.state = {}

    # Call tool
    result = set_routing_decision(
        company="google", interview_type="system_design", tool_context=tool_context
    )

    # Verify state
    assert tool_context.state["routing_decision"]["company"] == "google"
    assert tool_context.state["routing_decision"]["interview_type"] == "system_design"
    assert tool_context.state["routing_decision"]["confidence"] == 1.0
    assert tool_context.state["interview_phase"] == "intro"

    # Verify result message
    assert "google" in result.lower()
    assert "system_design" in result.lower()


def test_set_routing_decision_normalizes_case():
    """Test routing decision normalizes company and interview type to lowercase."""
    tool_context = MagicMock()
    tool_context.state = {}

    set_routing_decision(
        company="GOOGLE", interview_type="SYSTEM_DESIGN", tool_context=tool_context
    )

    assert tool_context.state["routing_decision"]["company"] == "google"
    assert tool_context.state["routing_decision"]["interview_type"] == "system_design"


def test_set_routing_decision_meta():
    """Test routing decision with Meta company."""
    tool_context = MagicMock()
    tool_context.state = {}

    result = set_routing_decision(
        company="Meta", interview_type="system_design", tool_context=tool_context
    )

    assert tool_context.state["routing_decision"]["company"] == "meta"
    assert "meta" in result.lower()
