# Interview Agent – Interview Orchestrator

Central Google ADK agent orchestrating multi-phase interviews using remote specialized agents via A2A protocol.

## Architecture

The interview-agent acts as an orchestrator that:
- Routes interviews based on company and type
- Delegates to remote interview agents (google-agent, meta-agent) via A2A protocol
- Falls back to local tools for legacy support (amazon)

```
interview-agent (orchestrator)
    ├── Routing Agent (LLM-powered)
    └── Interview Factory
        ├── Remote: google-agent (A2A) → http://localhost:10123
        ├── Remote: meta-agent (A2A) → http://localhost:10125
        └── Local: amazon-tools (legacy)
```

## Quick Start

1. **Prerequisites:** Python 3.10+, [uv](https://github.com/astral-sh/uv), and a Google API key with Gemini access.

2. **Start remote agents** (in separate terminals):
   ```bash
   # Terminal 1: Google agent
   cd services/google-agent
   uv run python -m google_agent

   # Terminal 2: Meta agent
   cd services/meta-agent
   uv run python -m meta_agent
   ```

3. **Install interview-agent** (from `services/interview-agent`):
   ```bash
   uv venv
   source .venv/bin/activate
   uv pip install -e ".[dev]"
   ```

4. **Configure secrets:** export `GOOGLE_API_KEY` or load it from a local `.env` (never commit secrets).

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

### Integration Tests
Integration tests verify complete interview flow with real LLM calls. Tests are split by phase to minimize costs.

```bash
# Run all integration tests
pytest tests/integration/test_interview_flow.py -v

# Run specific phase
pytest tests/integration/test_interview_flow.py::TestRoutingPhase -v
pytest tests/integration/test_interview_flow.py::TestIntroPhase -v
pytest tests/integration/test_interview_flow.py::TestDesignPhase -v

# Run with logs (shows tool calls, state changes)
pytest tests/integration/test_interview_flow.py::TestRoutingPhase -v -s --log-cli-level=INFO```

**What's tested:**
- ✅ Routing: Multi-turn conversation, `set_routing_decision` tool call
- ✅ Intro: Candidate info collection, `save_candidate_info` tool call, phase transitions
- ✅ Design: Multi-turn design conversations, phase progression, remote agent integration

**Test independence:** Later tests use helpers (`create_session_with_routing`, `create_session_with_candidate_info`) to bypass earlier phases, reducing LLM costs and test dependencies.

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
│       └── tools/                        # Tool definitions (local fallbacks)
├── shared/
│   ├── agents/                           # Intro/closing reusable agents
│   ├── agent_providers/                  # Remote A2A and local agent providers
│   ├── factories/                        # Interview and company factory patterns
│   │   ├── interview_factory.py          # Creates interview orchestrators
│   │   └── company_factory.py            # Routes to remote/local agents
│   ├── prompts/                          # External prompt templates
│   ├── schemas/                          # Pydantic data contracts
│   └── constants.py
└── ...

tests/
├── integration/                          # Record/replay E2E flow
└── interview_types/ & shared/            # Unit coverage mirroring package
```

## Architecture Highlights

- **A2A Protocol Integration:** Communicates with remote specialized agents via Agent-to-Agent protocol
- **Deterministic routing:** Root agent delegates based on persisted routing decisions
- **Phase orchestration:** System-design interviews flow through intro → design phases → closing
- **Hybrid approach:** Remote agents (google, meta) via A2A + legacy local tools (amazon)
- **Record/replay testing:** Integration coverage stays cheap and deterministic by reusing captured LLM responses

## Remote Agent Configuration

The interview agent dynamically discovers remote agents via environment variables. Copy `.env.example` to `.env` and configure:

```bash
# Required: List of agents to configure
INTERVIEW_AGENTS=google,meta

# For each agent, configure URL and supported interview types
GOOGLE_AGENT_URL=http://localhost:10123
GOOGLE_AGENT_TYPES=system_design,coding
GOOGLE_AGENT_DESCRIPTION=Google-style interviewer  # Optional

META_AGENT_URL=http://localhost:10125
META_AGENT_TYPES=system_design
META_AGENT_DESCRIPTION=Meta-style interviewer  # Optional
```

### Adding New Agents

To add a new remote agent (e.g., `amazon`):

1. Add the agent name to `INTERVIEW_AGENTS`: `INTERVIEW_AGENTS=google,meta,amazon`
2. Configure the agent's environment variables:
   ```bash
   AMAZON_AGENT_URL=http://localhost:10126
   AMAZON_AGENT_TYPES=system_design,behavioral
   AMAZON_AGENT_DESCRIPTION=Amazon-style interviewer  # Optional
   ```
3. Start the remote agent on the configured port
4. Restart the interview-agent to pick up the new configuration

The registry will automatically validate all required environment variables on startup.
