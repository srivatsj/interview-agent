import json
from typing import Any

import pytest

from google_agent.executor import GoogleAgentExecutor


class StubContext:
    def __init__(self, user_input: str) -> None:
        self._user_input = user_input

    def get_user_input(self) -> str:
        return self._user_input


class StubEventQueue:
    def __init__(self) -> None:
        self.events: list[Any] = []

    async def enqueue_event(self, event: Any) -> None:
        self.events.append(event)


def test_dispatch_get_phases_returns_phase_list() -> None:
    executor = GoogleAgentExecutor()

    response = executor._dispatch({"skill": "get_phases"})  # noqa: SLF001
    payload = json.loads(response)

    assert payload["status"] == "ok"
    assert payload["result"]["phases"][0]["id"] == "plan_and_scope"


def test_dispatch_evaluate_requires_phase_id() -> None:
    executor = GoogleAgentExecutor()

    response = executor._dispatch({"skill": "evaluate_phase"})  # noqa: SLF001
    payload = json.loads(response)

    assert payload["status"] == "error"
    assert payload["error"]["code"] == "missing_phase_id"


def test_dispatch_evaluate_requires_list_history() -> None:
    executor = GoogleAgentExecutor()

    response = executor._dispatch(
        {
            "skill": "evaluate",
            "args": {"phase_id": "plan_and_scope", "conversation_history": "oops"},
        }
    )  # noqa: SLF001
    payload = json.loads(response)

    assert payload["status"] == "error"
    assert payload["error"]["code"] == "invalid_history"


def test_dispatch_evaluate_invokes_toolset(monkeypatch: pytest.MonkeyPatch) -> None:
    executor = GoogleAgentExecutor()

    expected_history = [{"role": "user", "content": "plan approach architecture components"}]

    def fake_evaluate(phase_id: str, history: list[dict[str, Any]]) -> dict[str, Any]:
        assert phase_id == "plan_and_scope"
        assert history == expected_history
        return {"decision": "next_phase", "score": 7}

    monkeypatch.setattr(executor.toolset, "evaluate", fake_evaluate)

    response = executor._dispatch(
        {
            "skill": "evaluate_phase",
            "args": {
                "phase_id": "plan_and_scope",
                "conversation_history": expected_history,
            },
        }
    )  # noqa: SLF001
    payload = json.loads(response)

    assert payload["status"] == "ok"
    assert payload["result"]["evaluation"]["decision"] == "next_phase"


def test_dispatch_unknown_skill_reports_error() -> None:
    executor = GoogleAgentExecutor()

    response = executor._dispatch({"skill": "unknown"})  # noqa: SLF001
    payload = json.loads(response)

    assert payload["status"] == "error"
    assert payload["error"]["code"] == "unknown_skill"


@pytest.mark.asyncio
async def test_execute_handles_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    executor = GoogleAgentExecutor()
    context = StubContext("not-json")
    queue = StubEventQueue()

    monkeypatch.setattr("google_agent.executor.new_agent_text_message", lambda payload: payload)

    await executor.execute(context, queue)

    assert len(queue.events) == 1
    assert '"invalid_json"' in queue.events[0]


@pytest.mark.asyncio
async def test_execute_dispatches_when_payload_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    executor = GoogleAgentExecutor()
    context = StubContext('{"skill": "noop"}')
    queue = StubEventQueue()

    dispatched_payloads: list[dict[str, Any]] = []

    def fake_dispatch(self: GoogleAgentExecutor, payload: dict[str, Any]) -> str:  # noqa: D401
        dispatched_payloads.append(payload)
        return json.dumps({"status": "ok"})

    monkeypatch.setattr(
        "google_agent.executor.new_agent_text_message",
        lambda payload: payload,
    )
    monkeypatch.setattr(GoogleAgentExecutor, "_dispatch", fake_dispatch, raising=False)

    await executor.execute(context, queue)

    assert dispatched_payloads == [{"skill": "noop"}]
    assert queue.events == ['{"status": "ok"}']
