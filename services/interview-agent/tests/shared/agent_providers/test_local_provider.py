"""Tests for LocalAgentProvider wrapper."""

import pytest

from interview_agent.interview_types.system_design.tools import DefaultSystemDesignTools
from interview_agent.shared.agent_providers import LocalAgentProvider


@pytest.mark.asyncio
async def test_start_interview():
    """Test start_interview initializes session."""
    provider = DefaultSystemDesignTools()
    client = LocalAgentProvider(provider)

    result = await client.start_interview(
        interview_type="system_design",
        candidate_info={"name": "Jane Doe", "years_experience": 5},
    )

    assert result["status"] == "ok"
    assert result["result"]["interview_type"] == "system_design"
    assert result["result"]["candidate_info"]["name"] == "Jane Doe"


def test_get_phases():
    """Test get_phases delegates to underlying provider."""
    provider = DefaultSystemDesignTools()
    client = LocalAgentProvider(provider)

    phases = client.get_phases()

    assert len(phases) == 6
    assert phases[0]["id"] == "get_problem"
    assert phases[0]["name"] == "Problem Statement"


def test_get_context():
    """Test get_context delegates to underlying provider."""
    provider = DefaultSystemDesignTools()
    client = LocalAgentProvider(provider)

    context = client.get_context("problem_clarification")

    assert "Scale" in context or "scale" in context
    assert "DAU" in context or "QPS" in context


def test_evaluate():
    """Test evaluate delegates to underlying provider."""
    provider = DefaultSystemDesignTools()
    client = LocalAgentProvider(provider)

    conversation_history = [
        {"role": "user", "content": "I understand the problem, ready to proceed"}
    ]

    evaluation = client.evaluate_phase("get_problem", conversation_history)

    assert "decision" in evaluation
    assert "score" in evaluation
    assert evaluation["decision"] in ["continue", "next_phase"]


def test_evaluate_with_high_coverage():
    """Test evaluate returns next_phase when coverage is good."""
    provider = DefaultSystemDesignTools()
    client = LocalAgentProvider(provider)

    conversation_history = [
        {
            "role": "user",
            "content": "qps scale users latency availability geographic distribution",
        }
    ]

    evaluation = client.evaluate_phase("problem_clarification", conversation_history)

    assert evaluation["decision"] == "next_phase"
    assert evaluation["score"] >= 6


def test_evaluate_with_low_coverage():
    """Test evaluate returns continue when coverage is low."""
    provider = DefaultSystemDesignTools()
    client = LocalAgentProvider(provider)

    conversation_history = [{"role": "user", "content": "I have an idea"}]

    evaluation = client.evaluate_phase("problem_clarification", conversation_history)

    assert evaluation["decision"] == "continue"
    assert "gaps" in evaluation
    assert len(evaluation["gaps"]) > 0
