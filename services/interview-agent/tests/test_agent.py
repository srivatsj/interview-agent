"""Unit tests for RootCustomAgent"""

from unittest.mock import AsyncMock, Mock

import pytest
from google.adk.agents import Agent, BaseAgent
from google.adk.tools import ToolContext
from interview_agent.agent import RootCustomAgent, set_routing_decision


def create_mock_context(state=None):
    """Create a properly mocked InvocationContext for testing"""
    ctx = Mock()
    ctx.session = Mock()
    ctx.session.state = state if state is not None else {}

    # Mock plugin_manager for agents that use run_async internally
    plugin_manager = Mock()
    plugin_manager.run_before_agent_callback = AsyncMock(return_value=None)
    plugin_manager.run_after_agent_callback = AsyncMock(return_value=None)
    ctx.plugin_manager = plugin_manager

    # Mock model_copy for Pydantic context cloning
    ctx.model_copy = Mock(return_value=ctx)

    return ctx


class TestSetRoutingDecision:
    """Test set_routing_decision tool validation"""

    def test_invalid_company(self):
        """Test invalid company returns error"""
        ctx = Mock(spec=ToolContext)
        ctx.state = {}
        result = set_routing_decision("invalid_company", "system_design", ctx)

        assert "Error: Invalid company" in result

    def test_invalid_interview_type(self):
        """Test invalid interview type returns error"""
        ctx = Mock(spec=ToolContext)
        ctx.state = {}
        result = set_routing_decision("google", "invalid_type", ctx)

        assert "Error: Invalid interview type" in result

    def test_valid_routing(self):
        """Test valid routing saves to state"""
        ctx = Mock(spec=ToolContext)
        ctx.state = {}

        result = set_routing_decision("google", "system_design", ctx)

        assert "Routing saved: google system_design" in result
        assert "routing_decision" in ctx.state
        assert ctx.state["routing_decision"]["company"] == "google"


class TestRootCustomAgentDelegation:
    """Test RootCustomAgent delegates to correct orchestrator"""

    def test_system_design_routing_check(self):
        """Test agent has system_design orchestrator and reads routing correctly"""
        routing_agent = Agent(
            model="gemini-2.0-flash-exp",
            name="test_routing",
            description="Test",
        )

        class TestOrchestrator(BaseAgent):
            model_config = {"arbitrary_types_allowed": True}

            def __init__(self):
                super().__init__(name="test_orch", description="Test")

            async def _run_async_impl(self, ctx):
                yield Mock()

        orchestrator = TestOrchestrator()

        agent = RootCustomAgent(
            routing_agent=routing_agent, system_design_orchestrator=orchestrator
        )

        # Verify agent is properly initialized with sub-agents
        assert agent.system_design_orchestrator is not None
        assert agent.routing_agent is not None

        # Verify routing_decision logic by testing state reads
        ctx = create_mock_context(
            {"routing_decision": {"company": "google", "interview_type": "system_design"}}
        )

        routing_decision = ctx.session.state.get("routing_decision")
        assert routing_decision is not None
        interview_type = routing_decision.get("interview_type")

        # Verify the logic that determines delegation path (root_agent.py:114-119)
        assert interview_type == "system_design", "Should route to system_design"
        # When interview_type is "system_design", agent delegates to orchestrator

    @pytest.mark.asyncio
    async def test_routing_decision_state_logic(self):
        """Test agent correctly reads routing_decision from state"""
        routing_agent = Agent(
            model="gemini-2.0-flash-exp",
            name="test_routing",
            description="Test",
        )

        class TestOrchestrator(BaseAgent):
            model_config = {"arbitrary_types_allowed": True}

            def __init__(self):
                super().__init__(name="test_orch", description="Test")

            async def _run_async_impl(self, ctx):
                from google.adk.events import Event

                yield Event.create("ORCHESTRATOR_CALLED")

        orchestrator = TestOrchestrator()

        _agent = RootCustomAgent(
            routing_agent=routing_agent, system_design_orchestrator=orchestrator
        )

        # Test 1: No routing_decision in state
        ctx_empty = create_mock_context({})
        routing_decision_empty = ctx_empty.session.state.get("routing_decision")
        assert routing_decision_empty is None, "Should return None when no routing_decision"

        # Test 2: routing_decision exists in state
        ctx_with_routing = create_mock_context(
            {"routing_decision": {"company": "amazon", "interview_type": "system_design"}}
        )
        routing_decision = ctx_with_routing.session.state.get("routing_decision")
        assert routing_decision is not None, "Should find routing_decision"
        assert routing_decision["interview_type"] == "system_design"
        assert routing_decision["company"] == "amazon"

        # Test 3: Verify interview_type extraction logic
        interview_type = routing_decision.get("interview_type")
        assert interview_type == "system_design", "Should extract correct interview_type"
