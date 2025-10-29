import json
from typing import Any

import pytest

from meta_agent.agent import MetaAgent
from meta_agent.executor import MetaAgentExecutor


class StubContext:
    def __init__(self, user_input: str, context_id: str = "test-context-123") -> None:
        self._user_input = user_input
        self.context_id = context_id

    def get_user_input(self) -> str:
        return self._user_input


class StubEventQueue:
    def __init__(self) -> None:
        self.events: list[Any] = []

    async def enqueue_event(self, event: Any) -> None:
        self.events.append(event)


@pytest.mark.asyncio
async def test_execute_enqueues_dispatch_result(monkeypatch: pytest.MonkeyPatch) -> None:
    executor = MetaAgentExecutor()
    context = StubContext('{"skill": "get_phases"}')
    queue = StubEventQueue()

    monkeypatch.setattr("meta_agent.executor.new_agent_text_message", lambda payload: payload)

    dispatched: list[tuple[str, str, dict[str, Any]]] = []

    def fake_dispatch(
        self: MetaAgent, raw_input: str, context_id: str, sessions: dict[str, Any]
    ) -> str:  # noqa: D401
        dispatched.append((raw_input, context_id, sessions))
        return json.dumps({"status": "ok"})

    monkeypatch.setattr(MetaAgent, "dispatch", fake_dispatch, raising=False)

    await executor.execute(context, queue)

    assert len(dispatched) == 1
    assert dispatched[0][0] == '{"skill": "get_phases"}'  # raw_input
    assert dispatched[0][1] == "test-context-123"  # context_id
    assert queue.events == ['{"status": "ok"}']


@pytest.mark.asyncio
async def test_execute_handles_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    executor = MetaAgentExecutor()
    context = StubContext("not-json")
    queue = StubEventQueue()

    monkeypatch.setattr("meta_agent.executor.new_agent_text_message", lambda payload: payload)

    await executor.execute(context, queue)

    assert len(queue.events) == 1
    payload = json.loads(queue.events[0])
    assert payload["status"] == "error"
    assert payload["error"]["code"] == "invalid_json"
