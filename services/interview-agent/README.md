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
