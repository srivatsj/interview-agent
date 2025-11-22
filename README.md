# Interview Agent

AI-powered technical interview platform with real-time audio, collaborative canvas, and multi-agent orchestration using Google ADK and Gemini 2.5 Flash Native Audio.

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│         Frontend (Next.js 16, port 3000)                │
│  ┌────────────┐  ┌──────────┐  ┌────────────────────┐  │
│  │ Excalidraw │  │  Monaco  │  │  Audio Worklets    │  │
│  │ Whiteboard │  │  Editor  │  │  (16kHz → 24kHz)   │  │
│  └────────────┘  └──────────┘  └────────────────────┘  │
└─────────────────────┬───────────────────────────────────┘
                      │ WebSocket (Audio PCM + Canvas PNG)
                      ▼
┌─────────────────────────────────────────────────────────┐
│    Interview Orchestrator (Python ADK, port 8000)       │
│                                                         │
│       Root Coordinator (Phase Router)                   │
│           ├── Routing (Company + Payment)               │
│           ├── Intro (Candidate Info)                    │
│           ├── Interview (Design/Coding)                 │
│           └── Closing (Feedback)                        │
└─────────────────────┬───────────────────────────────────┘
                      │ A2A Protocol (HTTP/JSON)
                      ▼
┌─────────────────────────────────────────────────────────┐
│             Remote Agents (A2A + AP2)                   │
│  ┌─────────────────┐         ┌─────────────────┐       │
│  │  Google Agent   │         │   Meta Agent    │       │
│  │  (port 8001)    │         │   (port 8002)   │       │
│  │ • Interview     │         │ • Interview     │       │
│  │ • Payment       │         │ • Payment       │       │
│  └─────────────────┘         └─────────────────┘       │
└─────────────────────────────────────────────────────────┘
```

## Core Features

### Real-time Audio (Gemini 2.5 Flash Native Audio)
- Bidirectional streaming (16kHz PCM upload, 24kHz PCM playback)
- AudioWorklet processors for low-latency processing
- Voice Activity Detection (VAD) for barge-in/interruption
- Audio mixing for recording (mic + agent)

### Dual Canvas System
- **Excalidraw**: Whiteboard for system design diagrams
- **Monaco**: Code editor with multi-language support
- Tabbed interface (switch between whiteboard/code)
- Canvas stream capture for video recording

### Multi-Agent Orchestration
- Phase-based routing: routing → intro → interview → closing → done
- InMemory sessions during interview (zero latency)
- PostgreSQL sync on disconnect (text transcriptions only)
- Remote agent integration via A2A protocol

### Payment Processing (AP2)
- Cart mandates from remote agents (merchant role)
- Payment confirmation via frontend (credentials provider role)
- Stripe integration with encrypted payment tokens
- Transaction persistence in PostgreSQL

### Recording & Persistence
- Composite video: Canvas (full frame) + Webcam (PiP)
- Mixed audio: Microphone + Agent speech
- VP9 + Opus codec (2.5 Mbps)
- Upload to Vercel Blob storage

## Quick Start

### Prerequisites
- Node.js 20+
- Python 3.14+
- PostgreSQL
- Google API Key (Gemini)
- Stripe Account (for payments)

### 1. Frontend
```bash
cd services/frontend
npm install
cp .env.example .env  # Configure DATABASE_URL, STRIPE_*, GOOGLE_API_KEY

# Database setup
npm run db:generate  # Generate migrations from schema
npm run db:push      # Push schema to database (or use: npm run db)

npm run dev  # http://localhost:3000
```

### 2. Interview Orchestrator
```bash
cd services/interview-orchestrator
uv venv && source .venv/bin/activate
uv pip install -e .
cp .env.example .env  # Configure GOOGLE_API_KEY, DATABASE_URL, FRONTEND_URL
python -m uvicorn interview_orchestrator.server:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Remote Agents (Optional)
```bash
# Google Agent
cd services/google-agent
uv venv && source .venv/bin/activate
uv pip install -e .
cp .env.example .env  # Configure GOOGLE_API_KEY, FRONTEND_URL
uvicorn main:app --host 0.0.0.0 --port 8001

# Meta Agent
cd services/meta-agent
uv venv && source .venv/bin/activate
uv pip install -e .
cp .env.example .env  # Configure GOOGLE_API_KEY, FRONTEND_URL
uvicorn main:app --host 0.0.0.0 --port 8002

# Configure orchestrator to use remote agents
# In services/interview-orchestrator/.env:
INTERVIEW_AGENTS=google,meta
GOOGLE_AGENT_URL=http://localhost:8001
GOOGLE_AGENT_TYPES=system_design,coding
META_AGENT_URL=http://localhost:8002
META_AGENT_TYPES=system_design
```

## Tech Stack

### Frontend
- **Framework**: Next.js 16, React 19, TypeScript
- **UI**: Tailwind CSS, Shadcn UI (Radix)
- **Canvas**: Excalidraw 0.18.0, Monaco Editor 4.7.0
- **Database**: PostgreSQL, Drizzle ORM 0.44.7
- **Auth**: Better-Auth 1.3.34 (GitHub, Google OAuth)
- **Payments**: Stripe 20.0.0
- **Storage**: Vercel Blob 2.0.0
- **Audio**: Web Audio API (AudioWorklet)

### Backend
- **Framework**: Python 3.14, FastAPI
- **AI**: Google ADK 1.16.0, Gemini 2.5 Flash Native Audio
- **Database**: PostgreSQL (Neon pooler compatible)
- **Protocols**: A2A SDK 0.3.0, AP2 (Agentic Payment Protocol v2)
- **HTTP**: HTTPX 0.27.0, Uvicorn 0.32.0

## Project Structure

```
interview-agent/
├── services/
│   ├── frontend/                  # Next.js app (port 3000)
│   │   ├── app/                  # App Router
│   │   │   ├── (auth)/           # Auth routes
│   │   │   ├── (dashboard)/      # Protected routes
│   │   │   ├── interview-session/ # Interview UI
│   │   │   └── api/              # API routes (auth, payments, upload)
│   │   ├── modules/              # Feature modules
│   │   │   ├── interview/        # Interview (audio, canvas, recording)
│   │   │   ├── home/             # Dashboard
│   │   │   ├── auth/             # Authentication
│   │   │   └── payments/         # Payment settings
│   │   ├── db/schema/            # Database schema
│   │   │   ├── users.ts          # Better-Auth tables
│   │   │   ├── interviews.ts     # Interview records
│   │   │   ├── canvas.ts         # Canvas state
│   │   │   └── payments.ts       # Stripe integration
│   │   └── public/               # AudioWorklet processors
│   │
│   ├── interview-orchestrator/    # Python ADK service (port 8000)
│   │   └── interview_orchestrator/
│   │       ├── websocket/        # WebSocket server
│   │       │   ├── app.py        # FastAPI + WebSocket endpoint
│   │       │   ├── session.py    # ADK session management
│   │       │   ├── events.py     # Event filtering/enrichment
│   │       │   ├── agent_to_client.py  # Agent → Client streaming
│   │       │   └── client_to_agent.py  # Client → Agent relay
│   │       ├── agents/           # Agent hierarchy
│   │       │   ├── routing.py    # Company selection + payment
│   │       │   ├── intro.py      # Candidate info
│   │       │   ├── interview.py  # Interview router
│   │       │   ├── closing.py    # Wrap-up
│   │       │   └── interview_types/
│   │       │       ├── design.py # System design agent
│   │       │       └── coding.py # Coding agent
│   │       └── shared/
│   │           ├── schemas/      # Pydantic models
│   │           ├── prompts/      # Prompt templates
│   │           └── infra/
│   │               ├── a2a/      # A2A protocol client
│   │               └── ap2/      # Payment processing
│   │
│   ├── google-agent/              # A2A agent (port 8001)
│   │   ├── main.py               # A2A server
│   │   ├── agent_executor.py     # Custom executor (routing)
│   │   └── tools/
│   │       ├── interview_tools.py  # LLM-based interview
│   │       └── payment_tools.py    # AP2 payment tools
│   │
│   └── meta-agent/                # A2A agent (port 8002)
│       └── (similar structure to google-agent)
│
└── README.md                       # This file
```

## Interview Flow

1. **User starts interview** → Frontend creates DB record
2. **WebSocket connects** → Orchestrator starts ADK session (InMemory)
3. **Routing phase** → Agent determines company/type + processes payment
4. **Intro phase** → Agent collects candidate background
5. **Interview phase** → Design/Coding agent conducts interview
   - Calls remote agents (Google/Meta) via A2A for company-specific feedback
6. **Closing phase** → Agent provides feedback and wraps up
7. **WebSocket disconnect** → Syncs session to PostgreSQL
8. **Recording uploaded** → Saved to Vercel Blob

## Inter-Service Communication

### Frontend ↔ Orchestrator
- **WebSocket**: `ws://localhost:8000/ws/{userId}?interview_id={id}&is_audio=true`
- **Messages**: Audio PCM (base64), text, canvas screenshots (PNG), payment confirmations
- **Response**: Structured agent events with audio/text parts + session state

### Orchestrator ↔ Remote Agents
- **Protocol**: A2A (HTTP/JSON)
- **Discovery**: Environment-based agent registry
- **Skills**: `conduct_interview`, `create_cart`, `process_payment`
- **Context**: Multi-turn conversation via `session_id`

### Remote Agents ↔ Frontend
- **Payment**: AP2 protocol via `POST /api/payments/execute`
- **Role**: Remote agents (merchants), Frontend (credentials provider)

### All Services ↔ Database
- **PostgreSQL**: Shared database with schema namespaces
- **Schemas**: `auth.*` (Better-Auth), `product.*` (interviews, canvas, payments), `public.*` (ADK sessions)

## Session Management

**During Interview**:
- InMemoryRunner for zero-latency performance
- State stored in `session.state` (interview_phase, routing_decision, candidate_info, etc.)
- Real-time audio/text streaming via WebSocket

**After Disconnect**:
- Filter events to text transcriptions only (reduces 50min → 2min sync)
- Enrich events with transcription data (ADK only persists `content` field)
- Batch sync to PostgreSQL (50-event chunks)
- Store session in `adk_sessions`, events in `adk_events`

## Payment Flow (AP2)

1. **Get Cart**: Orchestrator calls remote agent's `create_cart` skill → Cart mandate (JWT-signed, 15min expiry)
2. **Display**: Orchestrator sets `pending_confirmation` in state → Frontend shows payment UI
3. **Confirm**: User approves → Frontend calls orchestrator with confirmation
4. **Get Token**: Orchestrator calls `POST /api/payments/get-token` → Encrypted payment method token
5. **Execute**: Orchestrator creates payment mandate → Calls remote agent's `process_payment` skill
6. **Charge**: Remote agent forwards to `POST /api/payments/execute` → Frontend creates Stripe charge
7. **Receipt**: Frontend returns receipt → Remote agent → Orchestrator stores in state
8. **Continue**: Orchestrator transitions to `intro` phase

## Environment Variables

### Frontend
```bash
DATABASE_URL=postgresql://...
BETTER_AUTH_SECRET=...
BETTER_AUTH_URL=http://localhost:3000
GITHUB_CLIENT_ID=...
GITHUB_CLIENT_SECRET=...
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
BLOB_READ_WRITE_TOKEN=...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
```

### Interview Orchestrator
```bash
GOOGLE_API_KEY=...
AGENT_MODEL=gemini-2.5-flash-native-audio-preview-09-2025
DATABASE_URL=postgresql://...
FRONTEND_URL=http://localhost:3000
INTERVIEW_AGENTS=google,meta
GOOGLE_AGENT_URL=http://localhost:8001
GOOGLE_AGENT_TYPES=system_design,coding
META_AGENT_URL=http://localhost:8002
META_AGENT_TYPES=system_design
```

### Remote Agents
```bash
GOOGLE_API_KEY=...
AGENT_MODEL=gemini-2.0-flash-exp
FRONTEND_URL=http://localhost:3000
MERCHANT_SECRET=...  # For AP2 JWT signing
```

## Development

### Linting

**Frontend**:
```bash
cd services/frontend
npm run lint
npm run format
```

**Python Services**:
```bash
cd services/interview-orchestrator  # or google-agent, meta-agent
uv run ruff check .
uv run ruff format .
```

### Testing

**Frontend**:
```bash
cd services/frontend
npm test
```

**Orchestrator**:
```bash
cd services/interview-orchestrator
uv run pytest tests/ -v
```

### Database

**Schema Management**:
```bash
cd services/frontend
npm run db:generate  # Generate SQL migrations from schema
npm run db:push      # Push schema to database (or: npm run db)
npm run db:studio    # Visual DB explorer (Drizzle Studio)
```

## Key Implementation Details

### Audio Processing
- **Recording**: 16kHz PCM, AudioWorklet with VAD (energy threshold 0.05, speech duration 0.5s)
- **Playback**: 24kHz PCM, AudioWorklet with queue buffering and flush support
- **Transmission**: Base64-encoded PCM chunks via WebSocket
- **Barge-in**: VAD detects speech → flush playback → agent stops

### Canvas Capture
- **Stream**: 30 FPS canvas capture via `canvas.captureStream()`
- **Screenshot**: Periodic PNG snapshots (every 30s) → WebSocket → Backend
- **Persistence**: JSON state (elements + appState) → PostgreSQL

### Video Recording
- **Composite**: Canvas (1920x1080) + Webcam PiP (320x240, bottom-right)
- **Audio**: Mixed stream (mic + agent)
- **Format**: WebM (VP9 + Opus, 2.5 Mbps)
- **Upload**: Vercel Blob via `POST /api/interviews/[id]/upload-recording`

### Multi-Agent Coordination
- **Phase-based routing**: Root agent returns dynamic instruction based on `interview_phase`
- **State propagation**: All agents access `session.state` (read/write)
- **Sub-agent transfers**: ADK agent hierarchy for delegation
- **Remote agents**: Consumed as tools via A2A protocol

## Documentation

- **Root**: [README.md](README.md) - This file
- **Frontend**: [services/frontend/README.md](services/frontend/README.md), [agent.md](services/frontend/agent.md)
- **Orchestrator**: [services/interview-orchestrator/README.md](services/interview-orchestrator/README.md), [agent.md](services/interview-orchestrator/agent.md)
- **Google Agent**: [services/google-agent/README.md](services/google-agent/README.md), [agent.md](services/google-agent/agent.md)

**Note**: `README.md` files are human-readable, `agent.md` files are optimized for AI coding agents.
