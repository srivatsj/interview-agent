# Meta System Design Agent

A LangGraph-powered version of the Google-style deterministic system design interviewer.
It exposes the same skills as the original `google-agent` (`get_phases`, `get_context`,
`evaluate`, `evaluate_phase`) but uses a LangGraph state machine for skill routing.
The service remains A2A-compatible.

## Quick Start

1. **Prerequisites:** Python 3.10+, [uv](https://github.com/astral-sh/uv).
2. **Environment setup** (from `services/meta-agent`):
   ```bash
   uv venv
   source .venv/bin/activate
   uv pip install -e ".[dev]"
   ```
3. **Configuration:** Optional `.env` helper is provided; export any required API keys as needed.

### Running the Agent

```bash
python -m meta_agent --host 0.0.0.0 --port 10125
```

Send a smoke request (same payloads as the Google agent) while the server is running:

```bash
curl -X POST http://localhost:10125/ \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"message/send","params":{"message":{"messageId":"meta-test-1","role":"user","parts":[{"kind":"text","text":"{\"skill\": \"get_phases\"}"}]}}}'
```

`messageId` is mandatory for the A2A transport; any unique string works for local testing.

## Running Tests

### Unit Tests (fast, offline)
```bash
pytest tests/ -v
```
Useful targeted suites:
```bash
pytest tests/test_agent.py -v
pytest tests/test_executor.py -v
pytest tests/test_toolset.py -v
```

### Coverage
```bash
pytest tests/ --cov=meta_agent --cov-report=term-missing
```

### Integration Tests
No networked integration flows yet. Extend the JSON-RPC executor tests or introduce httpx-based smoke tests once remote behaviour evolves.

## Code Quality
```bash
ruff check .
ruff format .
pre-commit install         # optional: run hooks automatically
pre-commit run --all-files # run hooks on demand
```

## Features

- **LangGraph StateGraph** implementation for deterministic skill routing.
- **Plan-first onboarding** so the candidate must outline their approach before deeper
  technical exploration.
- **Deterministic skills** (`get_phases`, `get_context`, `evaluate_phase`) implemented
  without external LLM calls for predictable behaviour.
- **A2A compatible** thanks to the packaged `AgentCard` metadata and executor.

## Skill Invocation

Send JSON payloads in the message body when invoking through A2A:

| Skill            | Payload Example                                                                                                     | Description                                           |
| ---------------- | ------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- |
| `get_phases`     | `{"skill": "get_phases"}`                                                                                           | Returns the ordered Google phases.                    |
| `get_context`    | `{"skill": "get_context", "args": {"phase_id": "plan_and_scope"}}`                                                  | Guides what to cover in the current phase.            |
| `evaluate_phase` (`evaluate`) | `{"skill": "evaluate_phase", "args": {"phase_id": "plan_and_scope", "conversation_history": [{"role": "user", "content": "..."}]}}` | Scores coverage and surfaces follow-up suggestions.   |

Sample response:

```json
{
  "status": "ok",
  "skill": "get_phases",
  "result": {
    "phases": [
      {"id": "plan_and_scope", "name": "Plan & High-Level Scope"},
      {"id": "requirements_alignment", "name": "Requirements Alignment"}
    ]
  }
}
```

## Project Layout

```
meta_agent/
├── __main__.py   # Click entrypoint wiring the AgentCard and uvicorn server
├── agent.py      # LangGraph StateGraph implementation for skill routing
├── executor.py   # Routes incoming JSON payloads through the LangGraph agent
└── toolset.py    # Phase catalogue, context prompts, and keyword evaluation

tests/
├── test_agent.py
├── test_executor.py
└── test_toolset.py
```
