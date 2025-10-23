"""Tests for intro_agent"""

from unittest.mock import Mock

from google.adk.tools import ToolContext
from root_agent.shared.agents.intro_agent import save_candidate_info


class TestSaveCandidateInfo:
    """Test save_candidate_info tool"""

    def test_saves_to_session_state(self):
        """Test candidate info is saved to session state"""
        ctx = Mock(spec=ToolContext)
        ctx.session.state = {}

        result = save_candidate_info(
            tool_context=ctx,
            name="Alice Smith",
            years_experience=5,
            domain="distributed systems",
            projects="E-commerce platform, Payment gateway",
        )

        assert "Candidate info saved" in result
        assert "candidate_info" in ctx.session.state
        assert ctx.session.state["candidate_info"]["name"] == "Alice Smith"
        assert ctx.session.state["candidate_info"]["years_experience"] == 5
        assert ctx.session.state["candidate_info"]["domain"] == "distributed systems"

    def test_validates_experience(self):
        """Test years_experience must be non-negative"""
        ctx = Mock(spec=ToolContext)
        ctx.session.state = {}

        try:
            save_candidate_info(
                tool_context=ctx,
                name="Bob",
                years_experience=-1,  # Invalid
                domain="frontend",
                projects="React app",
            )
            assert False, "Should have raised validation error"
        except Exception as e:
            assert (
                "validation error" in str(e).lower()
                or "greater than or equal to 0" in str(e).lower()
            )
