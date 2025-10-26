"""Tests for PhaseAgent"""

from interview_agent.interview_types.system_design.phase_agent import PhaseAgent
from interview_agent.interview_types.system_design.tools.amazon_tools import (
    AmazonSystemDesignTools,
)


class MockToolContext:
    """Mock tool context for testing"""

    def __init__(self, state=None):
        self.state = state if state is not None else {}


class TestPhaseAgent:
    """Test PhaseAgent behavior"""

    def test_initialization_with_tools(self):
        """Test PhaseAgent initializes with tools"""
        tools = AmazonSystemDesignTools()
        agent = PhaseAgent(tools)

        assert agent.name == "phase_agent"
        assert agent.tool_provider == tools
        assert agent.description == "Conducts a single interview phase with multi-turn conversation"


class TestMarkPhaseCompleteTool:
    """Test mark_phase_complete tool function"""

    def test_marks_phase_complete_in_state(self):
        """Test mark_phase_complete sets phase_complete flag"""
        ctx = MockToolContext({"current_phase": "data_design"})
        result = PhaseAgent.mark_phase_complete(ctx)

        assert ctx.state["phase_complete"] is True
        assert "marked complete" in result.lower()

    def test_returns_confirmation_message(self):
        """Test mark_phase_complete returns confirmation"""
        ctx = MockToolContext({"current_phase": "requirements"})
        result = PhaseAgent.mark_phase_complete(ctx)

        assert "requirements" in result.lower()
        assert "complete" in result.lower()

    def test_handles_unknown_phase(self):
        """Test mark_phase_complete handles missing current_phase"""
        ctx = MockToolContext({})
        result = PhaseAgent.mark_phase_complete(ctx)

        # Should still set phase_complete and return message
        assert ctx.state["phase_complete"] is True
        assert "unknown" in result.lower()
