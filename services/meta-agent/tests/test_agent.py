"""Tests for the MetaAgent LangGraph implementation."""

import json

from meta_agent.agent import MetaAgent


def test_dispatch_get_phases() -> None:
    agent = MetaAgent()
    sessions = {}
    context_id = "test-context-1"

    # Start interview first
    agent.dispatch(
        '{"skill": "start_interview", "args": {"interview_type": "system_design", '
        '"candidate_info": {"name": "Test", "years_experience": 5}}}',
        context_id,
        sessions,
    )

    # Now get phases
    response = agent.dispatch('{"skill": "get_phases"}', context_id, sessions)
    payload = json.loads(response)

    assert payload["status"] == "ok"
    assert payload["result"]["phases"][0]["id"] == "plan_and_scope"


def test_dispatch_get_context() -> None:
    agent = MetaAgent()
    sessions = {}
    context_id = "test-context-2"

    # Start interview first
    agent.dispatch(
        '{"skill": "start_interview", "args": {"interview_type": "system_design", '
        '"candidate_info": {"name": "Test", "years_experience": 5}}}',
        context_id,
        sessions,
    )

    response = agent.dispatch(
        '{"skill": "get_context", "args": {"phase_id": "plan_and_scope"}}',
        context_id,
        sessions,
    )
    payload = json.loads(response)

    assert payload["status"] == "ok"
    assert "aligning on the interview plan" in payload["result"]["context"].lower()


def test_dispatch_evaluate() -> None:
    agent = MetaAgent()
    sessions = {}
    context_id = "test-context-3"

    # Start interview first
    agent.dispatch(
        '{"skill": "start_interview", "args": {"interview_type": "system_design", '
        '"candidate_info": {"name": "Test", "years_experience": 5}}}',
        context_id,
        sessions,
    )

    history = [{"role": "user", "content": "plan approach architecture components phase"}]
    request = {
        "skill": "evaluate",
        "args": {"phase_id": "plan_and_scope", "conversation_history": history},
    }
    response = agent.dispatch(json.dumps(request), context_id, sessions)
    payload = json.loads(response)

    assert payload["status"] == "ok"
    assert payload["result"]["evaluation"]["decision"] == "next_phase"


def test_dispatch_invalid_json() -> None:
    agent = MetaAgent()
    sessions = {}
    context_id = "test-context-4"

    response = agent.dispatch("not-json", context_id, sessions)
    payload = json.loads(response)

    assert payload["status"] == "error"
    assert payload["error"]["code"] == "invalid_json"


def test_dispatch_missing_phase_id_for_evaluate() -> None:
    agent = MetaAgent()
    sessions = {}
    context_id = "test-context-5"

    # Start interview first
    agent.dispatch(
        '{"skill": "start_interview", "args": {"interview_type": "system_design", '
        '"candidate_info": {"name": "Test", "years_experience": 5}}}',
        context_id,
        sessions,
    )

    response = agent.dispatch(
        '{"skill": "evaluate", "args": {"conversation_history": []}}',
        context_id,
        sessions,
    )
    payload = json.loads(response)

    assert payload["status"] == "error"
    assert payload["error"]["code"] == "missing_phase_id"
