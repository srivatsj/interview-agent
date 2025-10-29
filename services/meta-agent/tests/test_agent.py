"""Tests for the MetaAgent LangGraph implementation."""

import json

from meta_agent.agent import MetaAgent


def test_dispatch_get_phases() -> None:
    agent = MetaAgent()
    response = agent.dispatch('{"skill": "get_phases"}')
    payload = json.loads(response)

    assert payload["status"] == "ok"
    assert payload["result"]["phases"][0]["id"] == "plan_and_scope"


def test_dispatch_get_context() -> None:
    agent = MetaAgent()
    response = agent.dispatch('{"skill": "get_context", "args": {"phase_id": "plan_and_scope"}}')
    payload = json.loads(response)

    assert payload["status"] == "ok"
    assert "aligning on the interview plan" in payload["result"]["context"].lower()


def test_dispatch_evaluate() -> None:
    agent = MetaAgent()
    history = [{"role": "user", "content": "plan approach architecture components phase"}]
    request = {
        "skill": "evaluate",
        "args": {"phase_id": "plan_and_scope", "conversation_history": history}
    }
    response = agent.dispatch(json.dumps(request))
    payload = json.loads(response)

    assert payload["status"] == "ok"
    assert payload["result"]["evaluation"]["decision"] == "next_phase"


def test_dispatch_invalid_json() -> None:
    agent = MetaAgent()
    response = agent.dispatch("not-json")
    payload = json.loads(response)

    assert payload["status"] == "error"
    assert payload["error"]["code"] == "invalid_json"


def test_dispatch_missing_phase_id_for_evaluate() -> None:
    agent = MetaAgent()
    response = agent.dispatch('{"skill": "evaluate", "args": {"conversation_history": []}}')
    payload = json.loads(response)

    assert payload["status"] == "error"
    assert payload["error"]["code"] == "missing_phase_id"
