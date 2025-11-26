"""Unit tests for intro agent tools."""

from unittest.mock import MagicMock

import pytest

from interview_orchestrator.agents.intro import save_candidate_info


class TestSaveCandidateInfo:
    """Test save_candidate_info tool."""

    def test_saves_candidate_info_and_transitions_phase(self):
        """Test that candidate info is saved and phase transitions to interview."""
        tool_context = MagicMock()
        tool_context.state = {}

        result = save_candidate_info(
            name="Alice Chen",
            years_experience=8,
            domain="distributed systems",
            projects="Built real-time messaging platform, designed caching system",
            tool_context=tool_context,
        )

        # Check state updates
        assert tool_context.state["candidate_info"]["name"] == "Alice Chen"
        assert tool_context.state["candidate_info"]["years_experience"] == 8
        assert tool_context.state["candidate_info"]["domain"] == "distributed systems"
        assert "real-time messaging" in tool_context.state["candidate_info"]["projects"]

        # Check phase transition
        assert tool_context.state["interview_phase"] == "interview"

        # Check return message instructs transfer
        assert "Transfer to interview_coordinator" in result
