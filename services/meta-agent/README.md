# Meta System Design Agent

A LangGraph-powered version of the Google-style deterministic system design interviewer.
It exposes the same skills as the original `google-agent` (`get_phases`, `get_context`,
`evaluate`, `evaluate_phase`) but uses a LangGraph state machine instead of a bespoke
executor. The service remains A2A-compatible.

## Quick Start

1. **Prerequisites:** Python 3.10+, [uv](https://github.com/astral-sh/uv).
2. **Environment setup** (from `services/meta-agent`):
   ```bash
   uv venv
   source .venv/bin/activate
   uv pip install -e ".[dev]"
   ```
3. **Configuration:** Copy `.env.example` to `.env`. No model keys are required because
   the LangGraph graph is deterministic, but the file is left in place for parity with
   other services.

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

## Running Tests

No automated tests yet. Add `pytest` suites under `tests/` when behaviour evolves.

## Features

- **LangGraph StateGraph** implementation for deterministic skill routing.
- **Parity with Google agent skills**: same payload contract and JSON responses.
- **Drop-in executor** that mirrors the original service's JSON-RPC contract.

## Tests and Coverage

Run the unit tests:

```bash
pytest tests -q
```

Collect coverage data:

```bash
pytest tests --cov=meta_agent --cov-report=term-missing
```
