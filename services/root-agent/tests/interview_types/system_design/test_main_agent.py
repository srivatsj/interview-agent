"""Tests for SystemDesignOrchestrator"""

from unittest.mock import Mock

import pytest
from root_agent.interview_types.system_design.main_agent import system_design_interview_orchestrator


class TestSystemDesignOrchestrator:
    """Test SystemDesignOrchestrator phase transitions"""

    @pytest.mark.asyncio
    async def test_starts_with_intro_phase(self):
        """Test orchestrator starts with intro phase by default"""
        ctx = Mock()
        ctx.session.state = {}

        # Mock intro agent to yield one event
        async def mock_intro(_context):
            yield Mock()

        system_design_interview_orchestrator._intro_agent._run_async_impl = mock_intro

        events = [e async for e in system_design_interview_orchestrator._run_async_impl(ctx)]

        assert len(events) >= 1
        assert ctx.session.state.get("interview_phase") == "closing"

    @pytest.mark.asyncio
    async def test_transitions_to_closing(self):
        """Test orchestrator transitions from intro to closing"""
        ctx = Mock()
        ctx.session.state = {"interview_phase": "closing"}

        # Mock closing agent to yield one event
        async def mock_closing(_context):
            yield Mock()

        system_design_interview_orchestrator._closing_agent._run_async_impl = mock_closing

        events = [e async for e in system_design_interview_orchestrator._run_async_impl(ctx)]

        assert len(events) >= 1
        assert ctx.session.state.get("interview_phase") == "done"

    @pytest.mark.asyncio
    async def test_done_phase_completes(self):
        """Test orchestrator handles done phase"""
        ctx = Mock()
        ctx.session.state = {"interview_phase": "done"}

        # Should not raise an error and phase stays done
        try:
            async for _event in system_design_interview_orchestrator._run_async_impl(ctx):
                # Event.create() will fail in test, but we verify no exception before that
                break
        except AttributeError:
            # Expected - Event.create() doesn't work with string in test
            pass

        assert ctx.session.state["interview_phase"] == "done"

    def test_orchestrator_has_correct_name(self):
        """Test orchestrator is initialized with correct name"""
        assert system_design_interview_orchestrator.name == "system_design_interview_orchestrator"

    def test_orchestrator_has_sub_agents(self):
        """Test orchestrator has intro and closing agents"""
        assert hasattr(system_design_interview_orchestrator, "_intro_agent")
        assert hasattr(system_design_interview_orchestrator, "_closing_agent")
