import json
from typing import Any

import pytest

from meta_agent.agent import MetaAgent
from meta_agent.executor import MetaAgentExecutor


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


@pytest.mark.asyncio
async def test_execute_enqueues_dispatch_result(monkeypatch: pytest.MonkeyPatch) -> None:
    executor = MetaAgentExecutor()
    context = StubContext('{"skill": "get_phases"}')
    queue = StubEventQueue()

    monkeypatch.setattr("meta_agent.executor.new_agent_text_message", lambda payload: payload)

    dispatched: list[str] = []

    def fake_dispatch(self: MetaAgent, raw_input: str) -> str:  # noqa: D401
        dispatched.append(raw_input)
        return json.dumps({"status": "ok"})

    monkeypatch.setattr(MetaAgent, "dispatch", fake_dispatch, raising=False)

    await executor.execute(context, queue)

    assert dispatched == ['{"skill": "get_phases"}']
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
