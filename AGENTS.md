# Repository Guidelines

## Project Structure & Module Organization
- Core service lives in `services/interview-agent`. The `interview_agent/` package holds the entrypoint `root_agent.py`, reusable helpers in `shared/`, and system-design orchestration under `interview_types/system_design/` (orchestrator, phase agent, company tools, prompts).
- Tests mirror the package layout in `services/interview-agent/tests`; integration flows and their replay fixtures sit in `tests/integration/`.
- `samples/` hosts ADK reference agents for safe prototyping before promoting code into the service package.

## Build, Test, and Development Commands
- `uv venv && source .venv/bin/activate` — create and activate the Python 3.10 virtualenv.
- `uv pip install -e ".[dev]"` — install service and development extras (pytest, ruff, pre-commit).
- `pytest -v` — run the full suite (integration runs in replay mode by default).
- `RECORD_MODE=true pytest tests/integration/test_interview_flow.py -v` — refresh LLM-backed recordings.
- `ruff check .` / `ruff format .` — lint and format to the enforced style.

## Coding Style & Naming Conventions
- Target Python 3.10, line length 100, four-space indentation. Prefer double quotes and explicit top-level imports so Ruff passes cleanly.
- Keep module names snake_case, classes PascalCase, and private helpers prefixed with `_`. Mirror existing filenames in `shared/prompts` and `shared/schemas`.
- Run `pre-commit install` so lint and format checks fire automatically.

## Testing Guidelines
- Unit tests live under `tests/` with filenames `test_*.py`; mirror the package path and keep inputs deterministic.
- Integration flows use the record/replay harness in `tests/integration/llm_recorder.py`. Record after changing prompts, control flow, or tool contracts; replay otherwise to stay fast and offline.
- Use `pytest --cov=interview_agent --cov-report=term-missing` to check coverage on new features.

## Commit & Pull Request Guidelines
- Match the history: concise subject lines led by an action or qualifier, with short bullet points in the body when listing outcomes (e.g., “Refactor: …” or “test_complete_interview_journey - …”).
- Reference issues, flag updated recordings, and attach command output or screenshots for behavioral changes.
- Confirm Ruff, unit tests, and replay-mode integration tests pass; document any skipped checks and schedule re-recordings before merge.

## Environment & Secrets
- Export `GOOGLE_API_KEY` locally or via a `.env`; keep secrets and recordings with sensitive payloads out of source control.
- Toggle networked integration tests with `RECORD_MODE` and prune stale JSON fixtures once flows diverge.
