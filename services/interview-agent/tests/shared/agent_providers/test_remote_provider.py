"""Tests for RemoteAgentProvider using mocked httpx responses."""

import httpx
import pytest
import respx

from interview_agent.shared.agent_providers import RemoteAgentProvider
from tests.integration.providers.mock_remote_agent import MockA2AResponses


@pytest.mark.asyncio
@respx.mock
async def test_start_interview_success():
    """Test starting an interview session."""
    client = RemoteAgentProvider(agent_url="http://localhost:10123")

    # Mock the A2A endpoint
    respx.post("http://localhost:10123/a2a/invoke").mock(
        return_value=httpx.Response(200, json=MockA2AResponses.start_interview())
    )

    result = await client.start_interview(
        interview_type="system_design",
        candidate_info={"name": "Jane Doe", "years_experience": 5},
    )

    assert result["status"] == "ok"
    assert result["result"]["interview_type"] == "system_design"


@pytest.mark.asyncio
@respx.mock
async def test_get_phases_success():
    """Test getting interview phases."""
    client = RemoteAgentProvider(agent_url="http://localhost:10123")

    respx.post("http://localhost:10123/a2a/invoke").mock(
        return_value=httpx.Response(200, json=MockA2AResponses.get_phases())
    )

    phases = await client.get_phases()

    assert len(phases) == 3
    assert phases[0]["id"] == "plan_and_scope"
    assert phases[0]["name"] == "Plan & High-Level Scope"


@pytest.mark.asyncio
@respx.mock
async def test_get_context_success():
    """Test getting phase context."""
    client = RemoteAgentProvider(agent_url="http://localhost:10123")

    respx.post("http://localhost:10123/a2a/invoke").mock(
        return_value=httpx.Response(200, json=MockA2AResponses.get_context())
    )

    context = await client.get_context("plan_and_scope")

    assert "aligning on the interview plan" in context.lower()


@pytest.mark.asyncio
@respx.mock
async def test_get_question_success():
    """Test getting tailored interview question."""
    client = RemoteAgentProvider(agent_url="http://localhost:10123")

    respx.post("http://localhost:10123/a2a/invoke").mock(
        return_value=httpx.Response(200, json=MockA2AResponses.get_question())
    )

    question = await client.get_question()

    assert "5 years of experience" in question
    assert "url shortening" in question.lower()


@pytest.mark.asyncio
@respx.mock
async def test_evaluate_phase_continue():
    """Test phase evaluation with continue decision."""
    client = RemoteAgentProvider(agent_url="http://localhost:10123")

    respx.post("http://localhost:10123/a2a/invoke").mock(
        return_value=httpx.Response(200, json=MockA2AResponses.evaluate_phase_continue())
    )

    evaluation = await client.evaluate_phase(
        phase_id="plan_and_scope",
        conversation_history=[{"role": "user", "content": "I will design a system"}],
    )

    assert evaluation["decision"] == "continue"
    assert evaluation["score"] == 4
    assert "architecture" in evaluation["gaps"]


@pytest.mark.asyncio
@respx.mock
async def test_evaluate_phase_next():
    """Test phase evaluation with next_phase decision."""
    client = RemoteAgentProvider(agent_url="http://localhost:10123")

    respx.post("http://localhost:10123/a2a/invoke").mock(
        return_value=httpx.Response(200, json=MockA2AResponses.evaluate_phase_next())
    )

    evaluation = await client.evaluate_phase(
        phase_id="plan_and_scope",
        conversation_history=[
            {"role": "user", "content": "plan approach architecture components phase"}
        ],
    )

    assert evaluation["decision"] == "next_phase"
    assert evaluation["score"] == 8


@pytest.mark.asyncio
@respx.mock
async def test_remote_agent_error():
    """Test handling of remote agent errors."""
    client = RemoteAgentProvider(agent_url="http://localhost:10123")

    respx.post("http://localhost:10123/a2a/invoke").mock(
        return_value=httpx.Response(
            200, json=MockA2AResponses.error_response("no_session", "No active session")
        )
    )

    with pytest.raises(ValueError, match="Remote agent error: no_session"):
        await client.get_phases()


@pytest.mark.asyncio
@respx.mock
async def test_http_error_handling():
    """Test handling of HTTP errors."""
    client = RemoteAgentProvider(agent_url="http://localhost:10123")

    respx.post("http://localhost:10123/a2a/invoke").mock(
        return_value=httpx.Response(500, text="Internal Server Error")
    )

    with pytest.raises(httpx.HTTPStatusError):
        await client.get_phases()
