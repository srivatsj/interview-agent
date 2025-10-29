import json
from typing import Any

import pytest
from google.adk.sessions import Session

from google_agent.executor import GoogleAgentExecutor
from google_agent.tools.design_toolset import GoogleSystemDesignToolset


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


def create_test_session(
    session_id: str = "test-session", state: dict[str, Any] | None = None
) -> Session:
    """Create a test session with optional initial state."""
    return Session(
        app_name="test_app",
        user_id="test_user",
        id=session_id,
        state=state or {},
        events=[],
    )


@pytest.mark.asyncio
async def test_dispatch_get_supported_interview_types() -> None:
    executor = GoogleAgentExecutor(toolsets=[GoogleSystemDesignToolset])
    session = create_test_session()

    response = await executor._dispatch({"skill": "get_supported_interview_types"}, session)  # noqa: SLF001
    payload = json.loads(response)

    assert payload["status"] == "ok"
    assert "system_design" in payload["result"]["interview_types"]


@pytest.mark.asyncio
async def test_dispatch_start_interview_creates_session() -> None:
    executor = GoogleAgentExecutor(toolsets=[GoogleSystemDesignToolset])
    # Use executor's session service to create the session
    session = await executor._get_or_create_session("test-session-123")  # noqa: SLF001

    response = await executor._dispatch(
        {
            "skill": "start_interview",
            "args": {
                "interview_type": "system_design",
                "candidate_info": {
                    "name": "Jane Doe",
                    "years_experience": 5,
                    "domain": "distributed systems",
                },
            },
        },
        session,
    )  # noqa: SLF001
    payload = json.loads(response)

    assert payload["status"] == "ok"
    assert payload["result"]["interview_type"] == "system_design"
    # Get the updated session from the service
    updated_session = await executor.session_service.get_session(
        app_name=executor._app_name,  # noqa: SLF001
        user_id=executor._user_id,  # noqa: SLF001
        session_id="test-session-123",
    )
    assert updated_session.state["interview_type"] == "system_design"
    assert updated_session.state["candidate_info"]["name"] == "Jane Doe"


@pytest.mark.asyncio
async def test_dispatch_start_interview_validates_interview_type() -> None:
    executor = GoogleAgentExecutor(toolsets=[GoogleSystemDesignToolset])
    session = create_test_session()

    response = await executor._dispatch(
        {
            "skill": "start_interview",
            "args": {
                "interview_type": "invalid_type",
                "candidate_info": {},
            },
        },
        session,
    )  # noqa: SLF001
    payload = json.loads(response)

    assert payload["status"] == "error"
    assert payload["error"]["code"] == "unsupported_interview_type"


@pytest.mark.asyncio
async def test_dispatch_get_phases_requires_session() -> None:
    executor = GoogleAgentExecutor(toolsets=[GoogleSystemDesignToolset])
    session = create_test_session()  # Empty session, no interview_type

    response = await executor._dispatch({"skill": "get_phases"}, session)  # noqa: SLF001
    payload = json.loads(response)

    assert payload["status"] == "error"
    assert payload["error"]["code"] == "no_session"


@pytest.mark.asyncio
async def test_dispatch_get_phases_returns_phase_list() -> None:
    executor = GoogleAgentExecutor(toolsets=[GoogleSystemDesignToolset])
    session = create_test_session(state={"interview_type": "system_design", "candidate_info": {}})

    response = await executor._dispatch({"skill": "get_phases"}, session)  # noqa: SLF001
    payload = json.loads(response)

    assert payload["status"] == "ok"
    assert payload["result"]["phases"][0]["id"] == "plan_and_scope"


@pytest.mark.asyncio
async def test_dispatch_evaluate_requires_phase_id() -> None:
    executor = GoogleAgentExecutor(toolsets=[GoogleSystemDesignToolset])
    session = create_test_session(state={"interview_type": "system_design", "candidate_info": {}})

    response = await executor._dispatch({"skill": "evaluate_phase"}, session)  # noqa: SLF001
    payload = json.loads(response)

    assert payload["status"] == "error"
    assert payload["error"]["code"] == "missing_phase_id"


@pytest.mark.asyncio
async def test_dispatch_evaluate_requires_list_history() -> None:
    executor = GoogleAgentExecutor(toolsets=[GoogleSystemDesignToolset])
    session = create_test_session(state={"interview_type": "system_design", "candidate_info": {}})

    response = await executor._dispatch(
        {
            "skill": "evaluate",
            "args": {"phase_id": "plan_and_scope", "conversation_history": "oops"},
        },
        session,
    )  # noqa: SLF001
    payload = json.loads(response)

    assert payload["status"] == "error"
    assert payload["error"]["code"] == "invalid_history"


@pytest.mark.asyncio
async def test_dispatch_evaluate_invokes_toolset(monkeypatch: pytest.MonkeyPatch) -> None:
    executor = GoogleAgentExecutor(toolsets=[GoogleSystemDesignToolset])
    session = create_test_session(state={"interview_type": "system_design", "candidate_info": {}})

    expected_history = [{"role": "user", "content": "plan approach architecture components"}]

    def fake_evaluate(phase_id: str, history: list[dict[str, Any]]) -> dict[str, Any]:
        assert phase_id == "plan_and_scope"
        assert history == expected_history
        return {"decision": "next_phase", "score": 7}

    # Patch the system_design toolset instance
    monkeypatch.setattr(executor.toolsets["system_design"], "evaluate", fake_evaluate)

    response = await executor._dispatch(
        {
            "skill": "evaluate_phase",
            "args": {
                "phase_id": "plan_and_scope",
                "conversation_history": expected_history,
            },
        },
        session,
    )  # noqa: SLF001
    payload = json.loads(response)

    assert payload["status"] == "ok"
    assert payload["result"]["evaluation"]["decision"] == "next_phase"


@pytest.mark.asyncio
async def test_dispatch_unknown_skill_reports_error() -> None:
    executor = GoogleAgentExecutor(toolsets=[GoogleSystemDesignToolset])
    session = create_test_session(state={"interview_type": "system_design", "candidate_info": {}})

    response = await executor._dispatch({"skill": "unknown"}, session)  # noqa: SLF001
    payload = json.loads(response)

    assert payload["status"] == "error"
    assert payload["error"]["code"] == "unknown_skill"


@pytest.mark.asyncio
async def test_execute_handles_invalid_json(monkeypatch: pytest.MonkeyPatch) -> None:
    executor = GoogleAgentExecutor(toolsets=[GoogleSystemDesignToolset])
    context = StubContext("not-json")
    queue = StubEventQueue()

    monkeypatch.setattr("google_agent.executor.new_agent_text_message", lambda payload: payload)

    await executor.execute(context, queue)

    assert len(queue.events) == 1
    assert '"invalid_json"' in queue.events[0]


@pytest.mark.asyncio
async def test_execute_dispatches_when_payload_valid(monkeypatch: pytest.MonkeyPatch) -> None:
    executor = GoogleAgentExecutor(toolsets=[GoogleSystemDesignToolset])
    context = StubContext('{"skill": "noop"}')
    queue = StubEventQueue()

    dispatched_payloads: list[dict[str, Any]] = []
    dispatched_sessions: list[Session] = []

    async def fake_dispatch(
        self: GoogleAgentExecutor, payload: dict[str, Any], session: Session
    ) -> str:  # noqa: D401
        dispatched_payloads.append(payload)
        dispatched_sessions.append(session)
        return json.dumps({"status": "ok"})

    monkeypatch.setattr(
        "google_agent.executor.new_agent_text_message",
        lambda payload: payload,
    )
    monkeypatch.setattr(GoogleAgentExecutor, "_dispatch", fake_dispatch, raising=False)

    await executor.execute(context, queue)

    assert dispatched_payloads == [{"skill": "noop"}]
    assert len(dispatched_sessions) == 1
    assert dispatched_sessions[0].id == "test-context-123"
    assert queue.events == ['{"status": "ok"}']
