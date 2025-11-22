# Interview Orchestrator

WebSocket-based multi-agent interview service using Google ADK. Manages phase-based interviews with real-time audio streaming, remote agent integration (A2A), and payment processing (AP2).

## Architecture

```
Client (WebSocket) → Orchestrator (port 8000)
                        ↓
                Root Coordinator (phase router)
                        ↓
    ┌──────────────────┼──────────────────┐
    ▼                  ▼                  ▼
 Routing            Intro             Closing
  (payment)      (candidate info)   (feedback)
                     ↓
             Interview Router
                     ↓
         ┌──────────┴──────────┐
         ▼                     ▼
   Design Agent          Coding Agent
         │                     │
         └─────────A2A─────────┘
                   ▼
          Remote Agents (Google, Meta)
```

### Phase Flow
1. **routing**: Company selection + AP2 payment
2. **intro**: Collect candidate background
3. **interview**: System design or coding (calls remote agents via A2A)
4. **closing**: Feedback and wrap-up
5. **done**: Session complete

### Key Components

**WebSocket Layer** (`websocket/`)
- `app.py`: FastAPI server, WebSocket endpoint
- `session.py`: ADK session management (InMemory → PostgreSQL sync)
- `events.py`: Event filtering (text-only) and enrichment
- `agent_to_client.py`: Stream agent responses (audio/text)
- `client_to_agent.py`: Relay client messages (audio/text/confirmations)

**Agent Hierarchy** (`agents/`)
- `root_agent.py`: Phase-based coordinator
- `routing.py`: Company selection + payment (AP2)
- `intro.py`: Candidate info collection
- `interview.py`: Interview type router
- `interview_types/design.py`: System design with remote expert calls
- `interview_types/coding.py`: Coding with code execution + remote expert
- `closing.py`: Interview wrap-up

**Infrastructure** (`shared/infra/`)
- `a2a/agent_registry.py`: Remote agent discovery
- `a2a/remote_client.py`: A2A protocol client
- `ap2/payment_flow.py`: Payment processing
- `ap2/cart_helpers.py`: Cart mandate retrieval

## Setup

### Install
```bash
cd services/interview-orchestrator
uv venv && source .venv/bin/activate
uv pip install -e .
```

### Configure
```bash
cp .env.example .env
```

**Required Variables:**
```bash
# Google AI
GOOGLE_API_KEY=your_key_here
AGENT_MODEL=gemini-2.5-flash-native-audio-preview-09-2025

# Database
DATABASE_URL=postgresql://localhost:5432/interview_db

# Frontend (Credentials Provider for AP2)
FRONTEND_URL=http://localhost:3000

# Remote Agents (optional)
INTERVIEW_AGENTS=google,meta
GOOGLE_AGENT_URL=http://localhost:8001
GOOGLE_AGENT_TYPES=system_design,coding
META_AGENT_URL=http://localhost:8002
META_AGENT_TYPES=system_design
```

### Run
```bash
python -m uvicorn interview_orchestrator.server:app --host 0.0.0.0 --port 8000 --reload
```

### Lint
```bash
uv run ruff check interview_orchestrator/
uv run ruff format interview_orchestrator/
```

## WebSocket Protocol

**Endpoint**: `ws://localhost:8000/ws/{user_id}?interview_id={id}&is_audio=true`

**Client → Server:**
```json
// Audio (16kHz PCM)
{"mime_type": "audio/pcm", "data": "base64..."}

// Text
{"mime_type": "text/plain", "data": "Hello"}

// Payment confirmation
{"mime_type": "confirmation_response", "data": {"confirmation_id": "...", "approved": true}}

// Canvas screenshot
{"mime_type": "image/png", "data": "base64..."}
```

**Server → Client:**
```json
{
  "author": "agent",
  "is_partial": false,
  "turn_complete": true,
  "interrupted": false,
  "parts": [
    {"type": "audio/pcm", "data": "base64..."},
    {"type": "text", "data": "Welcome..."}
  ],
  "state": {
    "interview_phase": "intro",
    "routing_decision": {"company": "google", "interview_type": "system_design"},
    "candidate_info": {"name": "...", "years_experience": 5}
  }
}
```

## Session Management

**During Interview:**
- InMemoryRunner (zero latency)
- State stored in ADK session.state
- Real-time audio/text streaming

**After Disconnect:**
- Sync to PostgreSQL (text transcriptions only)
- Filter events via `should_sync_event()` (50min → 2min)
- Enrich events with transcriptions
- Batch sync in 50-event chunks

## A2A Integration

**Remote Agent Discovery:**
```python
# Configure via environment
GOOGLE_AGENT_URL=http://localhost:8001
GOOGLE_AGENT_TYPES=system_design,coding

# Call from interview agent
response = await call_remote_skill(
    agent_url=agent_url,
    text="Conduct interview",
    data={"message": "Design URL shortener", "session_id": "..."}
)
```

**Multi-turn Context:**
- `session_id` maintains conversation context
- Remote agent keeps state across turns
- Returns `TaskState.input_required` for continuation

## AP2 Payment Flow

1. **Get Cart**: Call remote agent's `create_cart` skill
2. **Display**: Set `pending_confirmation` in state → Frontend shows payment UI
3. **Confirm**: User approves → Frontend calls `/api/payments/get-token`
4. **Execute**: Create payment mandate → Call remote agent's `process_payment` skill
5. **Verify**: Store `payment_proof` in state → Transition to `intro` phase

## Code Structure

```
interview_orchestrator/
├── server.py                    # Entry point (logging config)
├── root_agent.py                # Root coordinator
├── websocket/                   # WebSocket layer
│   ├── app.py                  # FastAPI app + endpoints
│   ├── session.py              # ADK session lifecycle
│   ├── events.py               # Event filtering/enrichment
│   ├── agent_to_client.py      # Agent → Client streaming
│   └── client_to_agent.py      # Client → Agent relay
├── agents/                      # Agent hierarchy
│   ├── routing.py              # Company + payment
│   ├── intro.py                # Candidate info
│   ├── interview.py            # Interview router
│   ├── closing.py              # Wrap-up
│   └── interview_types/
│       ├── design.py           # System design
│       └── coding.py           # Coding
└── shared/                      # Shared modules
    ├── constants.py            # Gemini model config
    ├── session_store.py        # Active sessions dict
    ├── schemas/                # Pydantic models
    ├── prompts/                # Prompt templates
    └── infra/
        ├── a2a/                # A2A protocol
        └── ap2/                # Payment protocol
```

## Inter-Service Communication

**With Frontend:**
- WebSocket: Bidirectional audio/text streaming
- API Calls: Payment token retrieval (`/api/payments/get-token`)

**With Remote Agents:**
- A2A Protocol: HTTP/JSON skill invocation
- Skills: `conduct_interview`, `create_cart`, `process_payment`

**With Database:**
- PostgreSQL: Session persistence via ADK's DatabaseSessionService
- Tables: `adk_sessions`, `adk_events` (schema: public)
