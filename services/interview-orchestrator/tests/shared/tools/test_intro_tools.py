"""Unit tests for intro tools."""

from unittest.mock import MagicMock

from interview_orchestrator.shared.tools.intro_tools import save_candidate_info


def test_save_candidate_info():
    """Test candidate info tool saves info and transitions to design."""
    tool_context = MagicMock()
    tool_context.state = {}

    result = save_candidate_info(
        name="Alice Smith",
        years_experience=7,
        domain="distributed systems",
        projects="payment processing platforms",
        tool_context=tool_context,
    )

    # Verify state
    assert tool_context.state["candidate_info"]["name"] == "Alice Smith"
    assert tool_context.state["candidate_info"]["years_experience"] == 7
    assert tool_context.state["candidate_info"]["domain"] == "distributed systems"
    assert tool_context.state["candidate_info"]["projects"] == "payment processing platforms"
    assert tool_context.state["interview_phase"] == "design"

    # Verify result message
    assert "Alice Smith" in result
    assert "7 years" in result


def test_save_candidate_info_minimal():
    """Test candidate info with minimal experience."""
    tool_context = MagicMock()
    tool_context.state = {}

    save_candidate_info(
        name="Bob Lee",
        years_experience=1,
        domain="frontend",
        projects="social media app",
        tool_context=tool_context,
    )

    assert tool_context.state["candidate_info"]["name"] == "Bob Lee"
    assert tool_context.state["candidate_info"]["years_experience"] == 1


def test_save_candidate_info_senior():
    """Test candidate info with senior level experience."""
    tool_context = MagicMock()
    tool_context.state = {}

    save_candidate_info(
        name="Carol Chen",
        years_experience=15,
        domain="backend architecture",
        projects="microservices platform, distributed databases",
        tool_context=tool_context,
    )

    assert tool_context.state["candidate_info"]["years_experience"] == 15
    assert "microservices" in tool_context.state["candidate_info"]["projects"]
