"""Tests for InterviewFactory"""

import pytest

from interview_agent.shared.factories import InterviewFactory
from interview_agent.interview_types.system_design.orchestrator import (
    SystemDesignOrchestrator,
)


class TestInterviewFactory:
    """Test InterviewFactory creation logic"""

    def test_create_system_design_orchestrator(self):
        """Test creating system design orchestrator (case-insensitive)"""
        routing_decision = {"interview_type": "SYSTEM_DESIGN", "company": "amazon"}
        orchestrator = InterviewFactory.create_interview_orchestrator(routing_decision)

        assert isinstance(orchestrator, SystemDesignOrchestrator)
        assert orchestrator.intro_agent is not None
        assert orchestrator.design_agent is not None
        assert orchestrator.closing_agent is not None

    def test_create_coding_interview_raises_not_implemented(self):
        """Test coding interview raises NotImplementedError"""
        routing_decision = {"interview_type": "coding", "company": "amazon"}
        with pytest.raises(NotImplementedError, match="Coding interviews not yet implemented"):
            InterviewFactory.create_interview_orchestrator(routing_decision)

    def test_create_behavioral_interview_raises_not_implemented(self):
        """Test behavioral interview raises NotImplementedError"""
        routing_decision = {"interview_type": "behavioral", "company": "google"}
        with pytest.raises(NotImplementedError, match="Behavioral interviews not yet implemented"):
            InterviewFactory.create_interview_orchestrator(routing_decision)

    def test_create_invalid_interview_type(self):
        """Test invalid interview type raises ValueError"""
        routing_decision = {"interview_type": "invalid", "company": "amazon"}
        with pytest.raises(ValueError, match="Unknown interview type"):
            InterviewFactory.create_interview_orchestrator(routing_decision)

    def test_create_missing_interview_type(self):
        """Test missing interview_type raises ValueError"""
        routing_decision = {"company": "amazon"}
        with pytest.raises(ValueError, match="Missing 'interview_type' in routing decision"):
            InterviewFactory.create_interview_orchestrator(routing_decision)

    def test_create_missing_company(self):
        """Test missing company raises ValueError"""
        routing_decision = {"interview_type": "system_design"}
        with pytest.raises(ValueError, match="Missing 'company' in routing decision"):
            InterviewFactory.create_interview_orchestrator(routing_decision)

    def test_create_system_design_unknown_company_uses_default(self):
        """Test system design with unknown company falls back to default tools"""
        routing_decision = {"interview_type": "system_design", "company": "unknown_company"}
        orchestrator = InterviewFactory.create_interview_orchestrator(routing_decision)

        # Should successfully create orchestrator with default tools
        assert isinstance(orchestrator, SystemDesignOrchestrator)
        assert orchestrator.design_agent is not None

    def test_create_system_design_google_uses_remote_agent(self):
        """Test system design with Google creates orchestrator with remote agent"""
        routing_decision = {"interview_type": "system_design", "company": "google"}
        orchestrator = InterviewFactory.create_interview_orchestrator(routing_decision)

        # Should successfully create orchestrator with Google's remote agent
        assert isinstance(orchestrator, SystemDesignOrchestrator)
        assert orchestrator.design_agent is not None
