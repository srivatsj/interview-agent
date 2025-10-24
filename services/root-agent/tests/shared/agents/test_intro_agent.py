"""Tests for intro_agent"""

from unittest.mock import Mock

from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools import ToolContext
from root_agent.shared.agents.intro_agent import get_intro_instruction, save_candidate_info


class TestSaveCandidateInfo:
    """Test save_candidate_info tool"""

    def test_saves_to_session_state(self):
        """Test candidate info is saved to session state"""
        ctx = Mock(spec=ToolContext)
        # Create a real dict for state
        ctx.state = {}

        result = save_candidate_info(
            tool_context=ctx,
            name="Alice Smith",
            years_experience=5,
            domain="distributed systems",
            projects="E-commerce platform, Payment gateway",
        )

        assert "Candidate info saved" in result
        assert "candidate_info" in ctx.state
        assert ctx.state["candidate_info"]["name"] == "Alice Smith"
        assert ctx.state["candidate_info"]["years_experience"] == 5
        assert ctx.state["candidate_info"]["domain"] == "distributed systems"

    def test_validates_experience(self):
        """Test years_experience must be non-negative"""
        ctx = Mock(spec=ToolContext)
        ctx.state = {}

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


class TestGetIntroInstruction:
    """Test get_intro_instruction dynamic variable injection"""

    def test_injects_variables_from_state(self):
        """Test instruction injects company and interview_type from state"""
        # Create mock context with state
        ctx = Mock(spec=ReadonlyContext)
        ctx.session.state = {
            "routing_decision": {
                "company": "TechCorp",
                "interview_type": "System Design",
            },
        }

        instruction = get_intro_instruction(ctx)

        # Verify the template variables are replaced with actual values
        assert "TechCorp" in instruction
        assert "System Design" in instruction

        # Verify template placeholders are NOT present (after load_prompt's .format() call)
        assert "{routing_decision.company}" not in instruction
        assert "{routing_decision.interview_type}" not in instruction

    def test_uses_default_values_when_state_missing(self):
        """Test instruction uses fallback values when state is missing"""
        # Create mock context with empty state
        ctx = Mock(spec=ReadonlyContext)
        ctx.session.state = {}

        instruction = get_intro_instruction(ctx)

        # Should use default fallback values
        assert "COMPANY" in instruction
        assert "INTERVIEW_TYPE" in instruction

    def test_uses_defaults_when_keys_missing(self):
        """Test instruction uses fallback values when specific keys are missing"""
        # Create mock context with partial state
        ctx = Mock(spec=ReadonlyContext)
        ctx.session.state = {
            "routing_decision": {
                "company": "StartupXYZ",
                # interview_type missing
            },
        }

        instruction = get_intro_instruction(ctx)

        # Should have the provided value
        assert "StartupXYZ" in instruction
        # Should use default for missing value
        assert "INTERVIEW_TYPE" in instruction

    def test_instruction_contains_intro_content(self):
        """Test the generated instruction contains expected intro agent content"""
        ctx = Mock(spec=ReadonlyContext)
        ctx.session.state = {
            "routing_decision": {"company": "TestCo", "interview_type": "Backend"},
        }

        instruction = get_intro_instruction(ctx)

        # Verify it contains key intro agent content
        assert "greet" in instruction.lower() or "greeting" in instruction.lower()
        assert "collect" in instruction.lower() or "background" in instruction.lower()
        assert "save_candidate_info" in instruction
