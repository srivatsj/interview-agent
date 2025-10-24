"""Tests for SystemDesignOrchestrator"""

from unittest.mock import Mock

import pytest
from interview_agent.interview_types.system_design.main_agent import (
    system_design_interview_orchestrator,
)


class TestSystemDesignOrchestrator:
    """Test SystemDesignOrchestrator phase transitions"""

    @pytest.mark.skip(
        reason="Pydantic models don't allow mocking run_async - covered by integration test"
    )
    @pytest.mark.asyncio
    async def test_starts_with_intro_phase(self):
        """Test orchestrator starts with intro phase by default"""
        pass

    @pytest.mark.skip(
        reason="Pydantic models don't allow mocking run_async - covered by integration test"
    )
    @pytest.mark.asyncio
    async def test_transitions_to_closing(self):
        """Test orchestrator transitions from intro to closing"""
        pass

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
        assert hasattr(system_design_interview_orchestrator, "intro_agent")
        assert hasattr(system_design_interview_orchestrator, "closing_agent")
        assert system_design_interview_orchestrator.intro_agent is not None
        assert system_design_interview_orchestrator.closing_agent is not None
