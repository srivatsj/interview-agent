"""Tests for PhaseAgent with evaluation-based completion"""

from interview_agent.interview_types.system_design.phase_agent import PhaseAgent
from interview_agent.interview_types.system_design.tools.amazon_tools import (
    AmazonSystemDesignTools,
)


class TestPhaseAgent:
    """Test PhaseAgent initialization and configuration"""

    def test_initialization_with_tools(self):
        """Test PhaseAgent initializes correctly with tool provider"""
        tools = AmazonSystemDesignTools()
        agent = PhaseAgent(tools)

        assert agent.name == "phase_agent"
        assert agent.tool_provider == tools
        assert "evaluation" in agent.description.lower()  # Now uses evaluation-based completion

    def test_get_phase_instruction(self):
        """Test phase instruction generation includes context"""
        tools = AmazonSystemDesignTools()
        agent = PhaseAgent(tools)

        instruction = agent._get_phase_instruction("data_design")

        assert "data_design" in instruction.lower()
        assert "database" in instruction.lower()  # From phase context
        assert "schema" in instruction.lower()  # From phase context

    def test_extract_conversation_history_empty(self):
        """Test conversation extraction with no events"""
        from google.adk.sessions import Session

        tools = AmazonSystemDesignTools()
        agent = PhaseAgent(tools)

        # Mock context with empty session
        class MockContext:
            session = Session(id="test", app_name="test", user_id="test", state={}, events=[])

        ctx = MockContext()
        history = agent._extract_conversation_history(ctx)

        assert history == []

    def test_extract_conversation_history_with_messages(self):
        """Test conversation extraction with user and assistant messages"""
        from google.adk.events import Event
        from google.adk.sessions import Session
        from google.genai.types import Content, Part

        tools = AmazonSystemDesignTools()
        agent = PhaseAgent(tools)

        # Mock context with events
        class MockContext:
            session = Session(
                id="test",
                app_name="test",
                user_id="test",
                state={},
                events=[
                    Event(
                        author="user",
                        content=Content(parts=[Part(text="What is the scale?")]),
                    ),
                    Event(
                        author="assistant",
                        content=Content(parts=[Part(text="Let's discuss 10k QPS...")]),
                    ),
                ],
            )

        ctx = MockContext()
        history = agent._extract_conversation_history(ctx)

        assert len(history) == 2
        assert history[0]["role"] == "user"
        assert "scale" in history[0]["content"]
        assert history[1]["role"] == "assistant"
        assert "10k QPS" in history[1]["content"]


class TestPhaseEvaluation:
    """Test evaluation-based phase completion logic"""

    def test_evaluation_triggers_completion_on_good_coverage(self):
        """Test that good keyword coverage triggers phase completion"""
        tools = AmazonSystemDesignTools()

        # Conversation with good coverage (60%+ keywords)
        conversation = [
            {
                "role": "user",
                "content": "We need to handle 10k QPS with high availability for millions of users "
                "with low latency",
            }
        ]

        result = tools.evaluate("problem_clarification", conversation)

        assert result["decision"] == "next_phase"
        assert result["score"] >= 6  # 60%+ coverage

    def test_evaluation_continues_on_poor_coverage(self):
        """Test that poor keyword coverage continues the phase"""
        tools = AmazonSystemDesignTools()

        # Conversation with poor coverage
        conversation = [{"role": "user", "content": "Let's use a database"}]

        result = tools.evaluate("problem_clarification", conversation)

        assert result["decision"] == "continue"
        assert result["score"] < 6  # Less than 60% coverage
        assert "gaps" in result
        assert "followup_questions" in result


class TestPhaseContext:
    """Test phase context and topics"""

    def test_get_problem_phase_has_context(self):
        """Test get_problem phase has appropriate context"""
        tools = AmazonSystemDesignTools()
        context = tools.get_context("get_problem")

        assert "present" in context.lower()
        assert "problem" in context.lower()

    def test_all_phases_have_contexts(self):
        """Test all 6 phases have defined contexts"""
        tools = AmazonSystemDesignTools()
        phases = tools.get_phases()

        for phase in phases:
            context = tools.get_context(phase["id"])
            assert context is not None
            assert len(context) > 0
            assert context != "Discuss system design"  # Not the default

    def test_phases_have_evaluation_keywords(self):
        """Test all phases have evaluation keywords defined"""
        from interview_agent.interview_types.system_design.tools.amazon_tools import (
            EVALUATION_KEYWORDS,
        )

        tools = AmazonSystemDesignTools()
        phases = tools.get_phases()

        for phase in phases:
            assert phase["id"] in EVALUATION_KEYWORDS
            keywords = EVALUATION_KEYWORDS[phase["id"]]
            assert len(keywords) > 0
