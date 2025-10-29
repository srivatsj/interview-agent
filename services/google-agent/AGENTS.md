# Google Agent Catalog

| Agent | Purpose | Key Features | Launch Command |
| ----- | ------- | ------------ | -------------- |
| `google_agent` | Remote Google-style system design interviewer served via A2A protocol. | Deterministic skills (`get_phases`, `get_context`, `evaluate`, `evaluate_phase`) implemented without external LLM calls. Plan-first workflow enforcement. | `python -m google_agent --host 0.0.0.0 --port 10123` |

## Skills

- **get_phases**: Returns ordered interview phases
- **get_context**: Provides phase-specific guidance
- **evaluate / evaluate_phase**: Scores coverage and provides follow-up suggestions

## Architecture

Uses a custom executor that routes JSON payloads to deterministic toolset methods. No LLM dependencies.

