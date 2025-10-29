# Meta Agent Catalog

| Agent | Purpose | Key Features | Launch Command |
| ----- | ------- | ------------ | -------------- |
| `meta_agent` | Google-style system design interviewer implemented with LangGraph and served via A2A protocol. | LangGraph StateGraph for skill routing. Same deterministic skills as `google_agent`. Plan-first workflow enforcement. | `python -m meta_agent --host 0.0.0.0 --port 10125` |

## Skills

- **get_phases**: Returns ordered interview phases
- **get_context**: Provides phase-specific guidance
- **evaluate / evaluate_phase**: Scores coverage and provides follow-up suggestions

## Architecture

Uses LangGraph StateGraph to route incoming JSON payloads through a state machine. Provides same functionality as `google_agent` with a graph-based implementation. No LLM dependencies.
