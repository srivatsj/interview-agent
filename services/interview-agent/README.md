# Interview Agent – Interview Router

Custom Google ADK agent orchestrating multi-phase system-design interviews with deterministic control flow.

## Quick Start

1. **Prerequisites:** Python 3.10+, [uv](https://github.com/astral-sh/uv), and a Google API key with Gemini access.
2. **Create a virtual environment** (from `services/interview-agent`):
   ```bash
   uv venv
   source .venv/bin/activate
   uv pip install -e ".[dev]"
   ```
3. **Configure secrets:** export `GOOGLE_API_KEY` or load it from a local `.env` (never commit secrets).

## Running Tests

### Unit Tests (fast, offline)
```bash
pytest tests/ --ignore=tests/integration/ -v
```
Useful targeted suites:
```bash
pytest tests/test_root_agent.py -v
pytest tests/shared/agents/test_intro_agent.py -v
pytest tests/interview_types/system_design/test_orchestrator.py -v
```

### Coverage
```bash
pytest tests/ --ignore=tests/integration/ --cov=interview_agent --cov-report=term-missing
```

### Integration Tests (record/replay)
Use real Gemini calls only when refreshing fixtures.

```bash
# Record new responses (incurs API cost, ~20-30s)
RECORD_MODE=true pytest tests/integration/test_interview_flow.py -v

# Replay existing recordings (offline, ~5s)
pytest tests/integration/test_interview_flow.py -v
```
Re-run in record mode whenever prompts, control flow, or tool contracts change. Delete stale fixtures via `rm tests/integration/recordings/*.json` before re-recording.

## Code Quality

```bash
ruff check .
ruff format .
pre-commit install               # optional: run hooks automatically
pre-commit run --all-files       # run hooks on demand
```

## Project Structure

```
interview_agent/
├── root_agent.py                         # RootCustomAgent entrypoint
├── interview_types/
│   └── system_design/
│       ├── orchestrator.py               # Coordinates interview phases
│       ├── system_design_agent.py        # Company-specific orchestration
│       ├── phase_agent.py                # LLM-driven phase management
│       └── providers/                    # Tool definitions per company
├── shared/
│   ├── agents/                           # Intro/closing reusable agents
│   ├── prompts/                          # External prompt templates
│   ├── schemas/                          # Pydantic data contracts
│   └── constants.py
└── ...

tests/
├── integration/                          # Record/replay E2E flow
└── interview_types/ & shared/            # Unit coverage mirroring package
```

## Architecture Highlights

- **Deterministic routing:** Root agent delegates based on persisted routing decisions.
- **Phase orchestration:** System-design interviews flow through intro → design phases → closing.
- **Tool-backed state:** Providers encapsulate company-specific prompts, tools, and completion criteria.
- **Record/replay testing:** Integration coverage stays cheap and deterministic by reusing captured LLM responses.
