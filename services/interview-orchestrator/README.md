# Interview Agent – Interview Orchestrator

Central Google ADK agent orchestrating multi-phase interviews using remote specialized agents via A2A protocol.

## Architecture

The interview-orchestrator uses a **single-agent pattern with state-driven dynamic instruction** for seamless multi-phase interview flow:

```
interview-orchestrator (single LlmAgent with dynamic instruction)
    ├── State-Driven Delegation (via get_dynamic_instruction)
    │   ├── routing phase → routing tools
    │   ├── intro phase → intro tools
    │   ├── design phase → design tools
    │   └── closing phase → closing tools
    └── Company Factory (for design phase)
        ├── Remote: google-agent (A2A) → http://localhost:10123
        ├── Remote: meta-agent (A2A) → http://localhost:10125
        └── Local: default-tools (free tier)
```

**Key Features:**
- Single `LlmAgent` with dynamic instruction based on `interview_phase` state
- Tool-driven state transitions (routing → intro → design → closing → done)
- Live API (gemini-2.5-flash-native-audio-preview) for bidirectional audio/video
- No manual `run_live()` calls - ADK manages delegation automatically
- Persistent WebSocket connection throughout all phases

## Current Status

**✅ Implemented:**
- Single-agent pattern with state-driven instruction delegation
- Tool-based phase transitions (set_routing_decision, save_candidate_info, etc.)
- Live API WebSocket server with bidirectional streaming
- Session state management via ADK
- Unit tests for all tools (12 passing)
- Integration tests for state transitions (1 passing)
- A2A protocol support for remote company-specific agents

**📋 Architecture:**
- **Root Agent:** Single `LlmAgent` (`root_agent.py`)
- **Dynamic Instruction:** `get_dynamic_instruction()` returns phase-specific prompts
- **State Transitions:** Tools update `interview_phase` to trigger delegation changes
- **Phase Flow:** routing → intro → design → closing → done

**🔧 Remaining Work:**
- Implement bidirectional WebSocket with RunConfig and StreamingMode.BIDI
- Test audio interruptions with frontend integration
- Add more company-specific remote agents

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
ADK App (Single LlmAgent)
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
pytest tests/shared/tools/ -v
pytest tests/interview_types/system_design/ -v
pytest tests/shared/agent_providers/ -v
```

### Coverage
```bash
pytest tests/ --ignore=tests/integration/ --cov=interview_orchestrator --cov-report=term-missing
```

### Integration Tests

Integration tests verify complete interview flow using text messages (not audio).

**Run integration tests:**
```bash
pytest tests/integration/test_single_agent_flow.py -v
```

**Run with output:**
```bash
pytest tests/integration/test_single_agent_flow.py -v -s
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
├── root_agent.py                         # Single LlmAgent with dynamic instruction
├── server.py                             # WebSocket server (FastAPI + ADK)
├── interview_types/
│   └── system_design/
│       ├── design_agent_tool.py          # Design phase tools
│       └── tools/
│           └── default_tools.py          # Free tier implementation
├── shared/
│   ├── agent_providers/                  # Remote A2A and local providers
│   │   ├── protocol.py                   # InterviewAgentProtocol
│   │   ├── registry.py                   # AgentProviderRegistry
│   │   ├── remote_provider.py            # RemoteAgentProvider (A2A)
│   │   └── local_provider.py             # LocalAgentProvider (wrapper)
│   ├── factories/
│   │   └── company_factory.py            # Routes to remote/local agents
│   ├── prompts/                          # External prompt templates
│   │   ├── routing_agent.txt
│   │   ├── intro_agent.txt
│   │   ├── design_phase.txt
│   │   └── closing_agent.txt
│   ├── schemas/                          # Pydantic data contracts
│   │   ├── routing_decision.py
│   │   └── candidate_info.py
│   ├── tools/                            # Phase transition tools
│   │   ├── routing_tools.py              # set_routing_decision
│   │   ├── intro_tools.py                # save_candidate_info
│   │   └── closing_tools.py              # mark_interview_complete
│   └── constants.py
└── ...

tests/
├── integration/
│   └── test_single_agent_flow.py         # State transition tests (text-based)
├── interview_types/
│   └── system_design/
│       └── test_design_agent_tool.py     # Design tool tests
└── shared/
    ├── tools/                            # Tool unit tests
    │   ├── test_routing_tools.py
    │   ├── test_intro_tools.py
    │   └── test_closing_tools.py
    └── agent_providers/                  # Provider tests
        ├── test_registry.py
        ├── test_remote_provider.py
        └── test_local_provider.py
```

## Architecture Highlights

- **Single-Agent Pattern:** One `LlmAgent` with dynamic instruction based on `interview_phase` state
- **State-Driven Delegation:** `get_dynamic_instruction()` returns phase-specific prompts
- **Tool-Based Transitions:** Tools update state to trigger phase changes
- **A2A Protocol Integration:** Remote specialized agents via Agent-to-Agent protocol
- **Persistent Connection:** Single WebSocket session throughout all phases
- **Free + Paid Tiers:** Remote agents (Google, Meta) or free local default tools

### Phase Flow

The interview follows this state-driven flow:

1. **Routing Phase** (`interview_phase = "routing"` or undefined)
   - Tool: `set_routing_decision(company, interview_type)`
   - Action: Sets routing decision, transitions to `intro`

2. **Intro Phase** (`interview_phase = "intro"`)
   - Tool: `save_candidate_info(name, years_experience, domain, projects)`
   - Action: Saves candidate info, transitions to `design`

3. **Design Phase** (`interview_phase = "design"`)
   - Tool: `initialize_design_phase()` - loads interview question
   - Tool: `mark_design_complete()` - transitions to `closing`

4. **Closing Phase** (`interview_phase = "closing"`)
   - Tool: `mark_interview_complete()` - transitions to `done`

5. **Done** (`interview_phase = "done"`)
   - Interview complete

### How Dynamic Instruction Works

```python
def get_dynamic_instruction(ctx: ReadonlyContext) -> str:
    """Generate instruction based on current interview phase."""
    phase = ctx.session.state.get("interview_phase", "routing")

    if phase == "routing":
        return load_prompt("routing_agent.txt", ...)
    elif phase == "intro":
        return load_prompt("intro_agent.txt", ...)
    elif phase == "design":
        return load_prompt("design_phase.txt", ...)
    elif phase == "closing":
        return load_prompt("closing_agent.txt", ...)
    else:
        return "Interview is complete."
```

When a tool updates `interview_phase` in state, ADK automatically re-evaluates the instruction and adapts behavior - no manual orchestration needed!

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

## Bidirectional WebSocket with User Interruptions

To enable proper user interruption handling (user can interrupt AI mid-speech), configure the server with `StreamingMode.BIDI`:

```python
from google.genai.types import RunConfig, StreamingMode

# In server.py, pass RunConfig to run_live()
run_config = RunConfig(
    streaming_mode=StreamingMode.BIDI,  # Enable bidirectional streaming
)

# Pass to runner
runner.run_live(
    app_name="interview_orchestrator",
    user_id=user_id,
    session_id=session_id,
    run_config=run_config,
)
```

This enables:
- ✅ User can interrupt AI mid-speech
- ✅ AI stops speaking when interrupted
- ✅ AI processes user's interruption immediately
- ✅ Seamless turn-taking in voice conversations

See [ADK Custom Streaming WebSocket docs](https://google.github.io/adk-docs/streaming/custom-streaming-ws/) for implementation details.

---

**Built with [Google ADK](https://github.com/google/adk) - Agent Development Kit for building production-ready AI agents.**
