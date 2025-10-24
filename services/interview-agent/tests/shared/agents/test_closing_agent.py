"""Tests for closing_agent"""

from unittest.mock import Mock

from google.adk.agents.readonly_context import ReadonlyContext
from interview_agent.shared.agents.closing_agent import closing_agent, get_closing_instruction


class TestClosingAgent:
    """Test closing_agent initialization"""

    def test_agent_has_correct_name(self):
        """Test agent is initialized with correct name"""
        assert closing_agent.name == "closing_agent"

    def test_agent_has_description(self):
        """Test agent has description"""
        assert closing_agent.description
        assert (
            "wrap" in closing_agent.description.lower()
            or "close" in closing_agent.description.lower()
        )

    def test_agent_has_instruction(self):
        """Test agent has instruction prompt loaded"""
        assert closing_agent.instruction
        # instruction is now a callable function
        assert callable(closing_agent.instruction)


class TestGetClosingInstruction:
    """Test get_closing_instruction dynamic variable injection"""

    def test_injects_variables_from_state(self):
        """Test instruction injects company, interview_type, and candidate name from state"""
        # Create mock context with state
        ctx = Mock(spec=ReadonlyContext)
        ctx.session.state = {
            "routing_decision": {
                "company": "TechCorp",
                "interview_type": "System Design",
            },
            "candidate_info": {
                "name": "Alice Johnson",
            },
        }

        instruction = get_closing_instruction(ctx)

        # Verify the template variables are replaced with actual values
        assert "TechCorp" in instruction
        assert "System Design" in instruction
        assert "Alice Johnson" in instruction

        # Verify template placeholders are NOT present (after load_prompt's .format() call)
        assert "{routing_decision.company}" not in instruction
        assert "{routing_decision.interview_type}" not in instruction
        assert "{candidate_info.name}" not in instruction

    def test_uses_default_values_when_state_missing(self):
        """Test instruction uses fallback values when state is missing"""
        # Create mock context with empty state
        ctx = Mock(spec=ReadonlyContext)
        ctx.session.state = {}

        instruction = get_closing_instruction(ctx)

        # Should use default fallback values
        assert "COMPANY" in instruction
        assert "INTERVIEW_TYPE" in instruction
        assert "CANDIDATE" in instruction

    def test_uses_defaults_when_keys_missing(self):
        """Test instruction uses fallback values when specific keys are missing"""
        # Create mock context with partial state
        ctx = Mock(spec=ReadonlyContext)
        ctx.session.state = {
            "routing_decision": {
                "company": "StartupXYZ",
                # interview_type missing
            },
            # candidate_info missing
        }

        instruction = get_closing_instruction(ctx)

        # Should have the provided value
        assert "StartupXYZ" in instruction
        # Should use defaults for missing values
        assert "INTERVIEW_TYPE" in instruction
        assert "CANDIDATE" in instruction

    def test_instruction_contains_closing_content(self):
        """Test the generated instruction contains expected closing agent content"""
        ctx = Mock(spec=ReadonlyContext)
        ctx.session.state = {
            "routing_decision": {"company": "TestCo", "interview_type": "Backend"},
            "candidate_info": {"name": "Bob Smith"},
        }

        instruction = get_closing_instruction(ctx)

        # Verify it contains key closing agent content
        assert "wrap" in instruction.lower() or "close" in instruction.lower()
        assert "thank" in instruction.lower()
        assert "question" in instruction.lower()
