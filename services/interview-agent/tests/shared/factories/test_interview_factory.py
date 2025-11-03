"""Tests for InterviewFactory"""

import pytest

from interview_agent.interview_types.system_design.orchestrator import (
    SystemDesignOrchestrator,
)
from interview_agent.shared.factories import InterviewFactory


class TestInterviewFactory:
    """Test InterviewFactory creation logic"""

    @pytest.mark.asyncio
    async def test_create_system_design_orchestrator(self):
        """Test creating system design orchestrator (case-insensitive)"""
        routing_decision = {"interview_type": "SYSTEM_DESIGN", "company": "amazon"}
        orchestrator = await InterviewFactory.create_interview_orchestrator(routing_decision)

        assert isinstance(orchestrator, SystemDesignOrchestrator)
        assert orchestrator.intro_agent is not None
        assert orchestrator.design_agent is not None
        assert orchestrator.closing_agent is not None

    @pytest.mark.asyncio
    async def test_create_coding_interview_raises_not_implemented(self):
        """Test coding interview raises NotImplementedError"""
        routing_decision = {"interview_type": "coding", "company": "amazon"}
        with pytest.raises(NotImplementedError, match="Coding interviews not yet implemented"):
            await InterviewFactory.create_interview_orchestrator(routing_decision)

    @pytest.mark.asyncio
    async def test_create_behavioral_interview_raises_not_implemented(self):
        """Test behavioral interview raises NotImplementedError"""
        routing_decision = {"interview_type": "behavioral", "company": "google"}
        with pytest.raises(NotImplementedError, match="Behavioral interviews not yet implemented"):
            await InterviewFactory.create_interview_orchestrator(routing_decision)

    @pytest.mark.asyncio
    async def test_create_invalid_interview_type(self):
        """Test invalid interview type raises ValueError"""
        routing_decision = {"interview_type": "invalid", "company": "amazon"}
        with pytest.raises(ValueError, match="Unknown interview type"):
            await InterviewFactory.create_interview_orchestrator(routing_decision)

    @pytest.mark.asyncio
    async def test_create_missing_interview_type(self):
        """Test missing interview_type raises ValueError"""
        routing_decision = {"company": "amazon"}
        with pytest.raises(ValueError, match="Missing 'interview_type' in routing decision"):
            await InterviewFactory.create_interview_orchestrator(routing_decision)

    @pytest.mark.asyncio
    async def test_create_missing_company(self):
        """Test missing company raises ValueError"""
        routing_decision = {"interview_type": "system_design"}
        with pytest.raises(ValueError, match="Missing 'company' in routing decision"):
            await InterviewFactory.create_interview_orchestrator(routing_decision)

    @pytest.mark.asyncio
    async def test_create_system_design_unknown_company_uses_default(self):
        """Test system design with unknown company falls back to default tools"""
        routing_decision = {"interview_type": "system_design", "company": "unknown_company"}
        orchestrator = await InterviewFactory.create_interview_orchestrator(routing_decision)

        # Should successfully create orchestrator with default tools
        assert isinstance(orchestrator, SystemDesignOrchestrator)
        assert orchestrator.design_agent is not None
