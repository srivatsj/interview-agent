# Interview Agent – Interview Orchestrator

Central Google ADK agent orchestrating multi-phase interviews using remote specialized agents via A2A protocol.

## Architecture

The interview-orchestrator acts as an orchestrator that:
- Routes interviews based on company and type
- Delegates to remote interview agents (google-agent, meta-agent) via A2A protocol
- Falls back to local default tools for free tier support

```
interview-orchestrator (orchestrator)
    ├── Routing Agent (LLM-powered)
    ├── Intro Agent (collects candidate info)
    └── Interview Factory
        ├── Remote: google-agent (A2A) → http://localhost:10123
        ├── Remote: meta-agent (A2A) → http://localhost:10125
        └── Local: default-tools (free tier)
```

## Quick Start

1. **Prerequisites:** Python 3.10+, [uv](https://github.com/astral-sh/uv), and a Google API key with Gemini access.

2. **Start remote agents** (optional, for paid tier):
   ```bash
   # Terminal 1: Google agent
   cd services/google-agent
   uv run python -m google_agent

   # Terminal 2: Meta agent
   cd services/meta-agent
   uv run python -m meta_agent
   ```

3. **Install interview-orchestrator**:
   ```bash
   uv venv
   source .venv/bin/activate
   uv pip install -e ".[dev]"
   ```

4. **Configure secrets:** Export `GOOGLE_API_KEY` or load from `.env` (never commit secrets).

## WebSocket Server

The interview-orchestrator includes a WebSocket server for real-time interview sessions with bidirectional streaming of audio, screenshots, and text.

### Starting the Server

```bash
# Basic usage (default: 127.0.0.1:8080)
python -m interview_orchestrator

# Custom host and port
python -m interview_orchestrator --host 0.0.0.0 --port 3000

# Development mode with auto-reload
python -m interview_orchestrator --reload
```

### WebSocket Endpoint

**URL:** `ws://<host>:<port>/run_live`

**Query Parameters:**
- `app_name`: Always use `interview_orchestrator`
- `user_id`: Unique identifier for the user
- `session_id`: Unique identifier for the session

**Example Connection:**
```javascript
const ws = new WebSocket(
  'ws://localhost:8080/run_live?app_name=interview_orchestrator&user_id=user123&session_id=session456'
);
```

### Message Format

**From Frontend (Client → Server):**

Audio chunk (realtime mode):
```json
{
  "blob": {
    "mime_type": "audio/webm",
    "data": "<base64_encoded_audio>"
  }
}
```

Screenshot (realtime mode):
```json
{
  "blob": {
    "mime_type": "image/png",
    "data": "<base64_encoded_image>"
  }
}
```

Text message (turn-by-turn mode):
```json
{
  "content": {
    "parts": [{"text": "user message"}]
  }
}
```

**To Frontend (Server → Client):**

ADK Event objects serialized to JSON. Events include:
- `agent_content`: AI responses (text or audio)
- `tool_call`: Tool invocations
- `tool_result`: Tool results
- `state_update`: Session state changes

### Architecture

The WebSocket server leverages ADK's built-in infrastructure:
- **FastAPI** for HTTP and WebSocket handling
- **LiveRequestQueue** for bidirectional streaming
- **Session Management** via InMemorySessionService
- **Event Streaming** from ADK agents

```
Frontend (WebSocket Client)
    ↓↑ Audio/Screenshots/Text
WebSocket Server (/run_live)
    ↓↑ LiveRequestQueue
ADK App (RootCustomAgent)
    ↓↑ Agent Events
Gemini Live API
```

## Running Tests

### Unit Tests (fast, offline)
```bash
pytest tests/ --ignore=tests/integration/ -v
```

Targeted suites:
```bash
pytest tests/test_root_agent.py -v
pytest tests/shared/agents/test_intro_agent.py -v
pytest tests/interview_types/system_design/ -v
```

### Coverage
```bash
pytest tests/ --ignore=tests/integration/ --cov=interview_orchestrator --cov-report=term-missing
```

### Integration Tests

Integration tests verify complete interview flow with real LLM calls using LLM-generated candidate responses.

**Run all integration tests:**
```bash
pytest tests/integration/ -v
```

**Run specific test suites:**
```bash
# Individual phases (for debugging)
pytest tests/integration/test_interview_flow.py::TestRoutingPhase -v
pytest tests/integration/test_interview_flow.py::TestIntroPhase -v

# Complete E2E tests (with LLM candidate)
pytest tests/integration/test_e2e_interview.py::TestE2EInterview::test_e2e_interview_free_default -v -s
pytest tests/integration/test_e2e_interview.py::TestE2EInterview::test_e2e_interview_paid_remote -v -s
```

**View live conversation:**
```bash
pytest tests/integration/test_e2e_interview.py -v -s
```

#### Test Structure

**Individual Phase Tests** (for debugging):
- `TestRoutingPhase`: Routing decision logic
- `TestIntroPhase`: Candidate info collection

**E2E Tests** (realistic full flow):
- `test_e2e_interview_free_default`: Complete interview with free default agent
- `test_e2e_interview_paid_remote`: Complete interview with paid Google agent

#### LLM-Generated Candidate Responses

E2E tests use `CandidateResponseGenerator` to simulate realistic candidate behavior:
- ✅ No hardcoded responses
- ✅ Natural multi-turn conversations
- ✅ Realistic user experience testing
- ✅ Full conversation recordings

#### LLM Call Tracking & Costs

Latest test run metrics:

**`test_e2e_interview_free_default`:**
```
Total Interviewer LLM Calls: 7
Total Candidate LLM Calls: 6
Total LLM Calls: 13
Phases Completed: 3
Time: 2:20 minutes
Cost: ~$0.02-0.05 per run
```

Breakdown:
- Routing: 2 calls
- Intro: 3 calls (multi-turn)
- Design phases: 2 calls
- Candidate responses: 6 calls

#### Conversation Recordings

All tests save conversation recordings to `tests/integration/recording/*.json`:

```json
[
  {"role": "agent_name", "text": "message"},
  {"role": "user", "text": "response"}
]
```

## Code Quality

```bash
ruff check .
ruff format .
pre-commit install               # optional: auto-run hooks
pre-commit run --all-files       # run hooks on demand
```

## Project Structure

```
interview_orchestrator/
├── root_agent.py                         # RootCustomAgent entrypoint
├── interview_types/
│   └── system_design/
│       ├── system_design_agent.py        # Orchestrates multi-phase interview
│       ├── sub_agents/
│       │   └── phase_agent.py            # Interactive phase agent with turn-by-turn evaluation
│       └── tools/
│           └── default_tools.py          # Free tier implementation
├── shared/
│   ├── agents/                           # Intro/closing reusable agents
│   ├── agent_providers/                  # Remote A2A and local providers
│   ├── factories/
│   │   ├── interview_factory.py          # Creates interview orchestrators
│   │   └── company_factory.py            # Routes to remote/local agents
│   ├── prompts/                          # External prompt templates
│   ├── schemas/                          # Pydantic data contracts
│   └── constants.py
└── ...

tests/
├── integration/
│   ├── test_e2e_interview.py             # E2E tests with LLM candidate
│   ├── test_interview_flow.py            # Individual phase tests
│   ├── test_helpers.py                   # CandidateResponseGenerator
│   └── recording/                        # Conversation JSON files
└── interview_types/ & shared/            # Unit tests mirroring package
```

## Architecture Highlights

- **A2A Protocol Integration:** Remote specialized agents via Agent-to-Agent protocol
- **Deterministic Routing:** Root agent delegates based on persisted routing decisions
- **Phase Orchestration:** System-design flows through intro → design phases → closing
- **Interactive Phase Flow:** PhaseAgent evaluates after each user response (LLM speaks → user responds → evaluate → repeat)
- **Free + Paid Tiers:** Remote agents (Google, Meta) or free local default tools
- **Natural Testing:** E2E tests use LLM-generated candidate responses for realistic conversations
- **Question Integration:** Interview questions fetched once and injected into all phase prompts

## Remote Agent Configuration

Configure remote agents via environment variables. Copy `.env.example` to `.env`:

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

1. Add to `INTERVIEW_AGENTS`: `INTERVIEW_AGENTS=google,meta,amazon`
2. Configure environment variables:
   ```bash
   AMAZON_AGENT_URL=http://localhost:10126
   AMAZON_AGENT_TYPES=system_design,behavioral
   AMAZON_AGENT_DESCRIPTION=Amazon-style interviewer
   ```
3. Start the remote agent on the configured port
4. Restart interview-orchestrator to pick up the new configuration

The registry automatically validates all required environment variables on startup.
