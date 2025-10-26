"""Tests for SystemDesignOrchestrator"""

from typing import ClassVar
from unittest.mock import AsyncMock, Mock

import pytest
from google.adk.agents import Agent, BaseAgent

from interview_agent.interview_types.system_design.main_agent import SystemDesignOrchestrator


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


class TestSystemDesignOrchestrator:
    """Test SystemDesignOrchestrator phase transitions"""

    # Intro phase tests
    @pytest.mark.asyncio
    async def test_intro_phase_runs_intro_agent(self):
        """Test orchestrator runs intro agent when in intro phase - NO LLM CALLS"""
        from google.adk.events import Event

        # Create custom intro agent that tracks calls
        class MockIntroAgent(BaseAgent):
            model_config = {"arbitrary_types_allowed": True}
            called: ClassVar[bool] = False

            def __init__(self):
                super().__init__(name="mock_intro", description="Mock intro agent")

            async def run_async(self, _ctx):
                MockIntroAgent.called = True
                # Yield a mock event to cover the yield line
                yield Event(author=self.name)

        intro_agent = MockIntroAgent()
        closing_agent = Agent(model="dummy-model-no-llm", name="mock_closing")

        orchestrator = SystemDesignOrchestrator(
            intro_agent=intro_agent, closing_agent=closing_agent
        )

        # Create context with intro phase (default)
        ctx = create_mock_context({"interview_phase": "intro"})

        # Execute orchestrator
        async for _ in orchestrator._run_async_impl(ctx):
            pass

        # Verify intro agent was called
        assert MockIntroAgent.called, "Intro agent should have been called"

    @pytest.mark.asyncio
    async def test_intro_phase_transitions_to_design(self):
        """Test orchestrator transitions to design after intro completes - NO LLM CALLS"""

        class MockIntroAgent(BaseAgent):
            model_config = {"arbitrary_types_allowed": True}

            def __init__(self):
                super().__init__(name="mock_intro", description="Mock")

            async def run_async(self, _ctx):
                if False:
                    yield

        intro_agent = MockIntroAgent()
        closing_agent = Agent(model="dummy-model-no-llm", name="mock_closing")

        orchestrator = SystemDesignOrchestrator(
            intro_agent=intro_agent, closing_agent=closing_agent
        )

        # Create context with intro phase
        ctx = create_mock_context({"interview_phase": "intro"})

        # Execute orchestrator and collect events
        events = []
        async for event in orchestrator._run_async_impl(ctx):
            events.append(event)

        # Verify transition event was yielded
        assert any(
            hasattr(e, "actions")
            and e.actions
            and e.actions.state_delta
            and e.actions.state_delta.get("interview_phase") == "design"
            for e in events
        ), "Should transition to design phase"

    # Design phase tests
    @pytest.mark.asyncio
    async def test_design_phase_creates_and_runs_design_agent(self):
        """Test orchestrator creates design agent lazily and runs it - NO LLM CALLS"""
        intro_agent = Agent(model="dummy-model-no-llm", name="mock_intro")
        closing_agent = Agent(model="dummy-model-no-llm", name="mock_closing")

        orchestrator = SystemDesignOrchestrator(
            intro_agent=intro_agent, closing_agent=closing_agent
        )

        # Create context with design phase and routing_decision
        ctx = create_mock_context(
            {"interview_phase": "design", "routing_decision": {"company": "amazon"}}
        )

        # Execute orchestrator - should create design agent lazily
        events = []
        async for event in orchestrator._run_async_impl(ctx):
            events.append(event)

        # Verify design agent was created
        assert orchestrator._design_agent is not None, "Design agent should have been created"
        assert orchestrator._design_agent.name == "amazon_system_design_orchestrator"

    @pytest.mark.asyncio
    async def test_design_phase_transitions_to_closing_when_complete(self):
        """Test orchestrator transitions to closing when design complete - NO LLM CALLS"""
        from google.adk.events import Event

        class MockDesignAgent(BaseAgent):
            model_config = {"arbitrary_types_allowed": True}
            phases: ClassVar[list] = [{"id": "phase1"}]

            def __init__(self):
                super().__init__(name="mock_design", description="Mock")

            async def run_async(self, ctx):
                # Simulate design completion
                ctx.session.state["interview_phases_complete"] = True
                yield Event(author=self.name)

        intro_agent = Agent(model="dummy-model-no-llm", name="mock_intro")
        closing_agent = Agent(model="dummy-model-no-llm", name="mock_closing")

        orchestrator = SystemDesignOrchestrator(
            intro_agent=intro_agent, closing_agent=closing_agent
        )

        # Inject mock design agent to avoid lazy creation
        orchestrator._design_agent = MockDesignAgent()

        # Create context with design phase
        ctx = create_mock_context(
            {"interview_phase": "design", "routing_decision": {"company": "amazon"}}
        )

        # Execute orchestrator and collect events
        events = []
        async for event in orchestrator._run_async_impl(ctx):
            events.append(event)

        # Verify transition event was yielded
        assert any(
            hasattr(e, "actions")
            and e.actions
            and e.actions.state_delta
            and e.actions.state_delta.get("interview_phase") == "closing"
            for e in events
        ), "Should transition to closing phase"

    # Closing phase tests
    @pytest.mark.asyncio
    async def test_closing_phase_runs_closing_agent(self):
        """Test orchestrator runs closing agent when in closing phase - NO LLM CALLS"""
        from google.adk.events import Event

        # Create custom closing agent that tracks calls
        class MockClosingAgent(BaseAgent):
            model_config = {"arbitrary_types_allowed": True}
            called: ClassVar[bool] = False

            def __init__(self):
                super().__init__(name="mock_closing", description="Mock closing agent")

            async def run_async(self, _ctx):
                MockClosingAgent.called = True
                # Yield a mock event to cover the yield line
                yield Event(author=self.name)

        intro_agent = Agent(model="dummy-model-no-llm", name="mock_intro")
        closing_agent = MockClosingAgent()

        orchestrator = SystemDesignOrchestrator(
            intro_agent=intro_agent, closing_agent=closing_agent
        )

        # Create context with closing phase
        ctx = create_mock_context({"interview_phase": "closing"})

        # Execute orchestrator
        async for _ in orchestrator._run_async_impl(ctx):
            pass

        # Verify closing agent was called
        assert MockClosingAgent.called, "Closing agent should have been called"

    @pytest.mark.asyncio
    async def test_closing_phase_transitions_to_done(self):
        """Test orchestrator transitions to done after closing - NO LLM CALLS"""

        class MockClosingAgent(BaseAgent):
            model_config = {"arbitrary_types_allowed": True}

            def __init__(self):
                super().__init__(name="mock_closing", description="Mock")

            async def run_async(self, _ctx):
                if False:
                    yield

        intro_agent = Agent(model="dummy-model-no-llm", name="mock_intro")
        closing_agent = MockClosingAgent()

        orchestrator = SystemDesignOrchestrator(
            intro_agent=intro_agent, closing_agent=closing_agent
        )

        # Create context with closing phase
        ctx = create_mock_context({"interview_phase": "closing"})

        # Execute orchestrator and collect events
        events = []
        async for event in orchestrator._run_async_impl(ctx):
            events.append(event)

        # Verify transition event was yielded
        assert any(
            hasattr(e, "actions")
            and e.actions
            and e.actions.state_delta
            and e.actions.state_delta.get("interview_phase") == "done"
            for e in events
        ), "Should transition to done phase"

    # Done phase test
    @pytest.mark.asyncio
    async def test_done_phase_completes_without_error(self):
        """Test orchestrator handles done phase without error - NO LLM CALLS"""
        intro_agent = Agent(model="dummy-model-no-llm", name="mock_intro")
        closing_agent = Agent(model="dummy-model-no-llm", name="mock_closing")

        orchestrator = SystemDesignOrchestrator(
            intro_agent=intro_agent, closing_agent=closing_agent
        )

        # Create context with done phase
        ctx = create_mock_context({"interview_phase": "done"})

        # Execute orchestrator - should complete without raising exception
        event_count = 0
        async for _ in orchestrator._run_async_impl(ctx):
            event_count += 1

        # Verify no events yielded (done phase just logs)
        assert event_count == 0
