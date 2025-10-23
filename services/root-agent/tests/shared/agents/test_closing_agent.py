"""Tests for closing_agent"""

from root_agent.shared.agents.closing_agent import closing_agent


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
        assert len(closing_agent.instruction) > 0
