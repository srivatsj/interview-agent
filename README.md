# Interview Agent

> AI-powered technical interview platform with real-time audio, collaborative canvas, and multi-agent orchestration.

Practice system design interviews with AI agents that provide company-specific feedback using Google ADK and Gemini 2.5 Flash Native Audio.

---

## 🏗️ Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                  FRONTEND (Next.js 16 + React 19)              │
│                      http://localhost:3000                      │
│                                                                 │
│  ┌────────────┐  ┌──────────┐  ┌─────────┐  ┌──────────────┐ │
│  │ Excalidraw │  │  Webcam  │  │  Audio  │  │  Recording   │ │
│  │   Canvas   │  │  Stream  │  │ Worklet │  │ (WebM video) │ │
│  └─────┬──────┘  └────┬─────┘  └────┬────┘  └──────┬───────┘ │
│        │              │               │              │         │
│        └──────────────┴───────────────┴──────────────┘         │
│                       │                                         │
└───────────────────────┼─────────────────────────────────────────┘
                        │
                        │ WebSocket (Audio PCM + Canvas PNG)
                        │ ws://localhost:8000/ws/{userId}
                        ▼
┌─────────────────────────────────────────────────────────────────┐
│          ORCHESTRATOR (Python + Google ADK 1.16.0)             │
│                    http://localhost:8000                        │
│                                                                 │
│            ┌──────────────────────────┐                        │
│            │   Root Coordinator       │                        │
│            │   (Phase Manager)        │                        │
│            └────────┬─────────────────┘                        │
│                     │                                           │
│       ┌─────────────┼─────────────┐                            │
│       ▼             ▼             ▼                            │
│  ┌─────────┐  ┌─────────┐  ┌──────────┐                       │
│  │ Routing │  │  Intro  │  │ Closing  │                       │
│  │  Agent  │  │  Agent  │  │  Agent   │                       │
│  └─────────┘  └─────────┘  └──────────┘                       │
│                     │                                           │
│              ┌──────┴─────┐                                    │
│              ▼            ▼                                    │
│      ┌────────────┐  ┌──────────┐                             │
│      │   Design   │  │  Coding  │                             │
│      │   Agent    │  │  Agent   │                             │
│      └─────┬──────┘  └──────────┘                             │
│            │                                                    │
└────────────┼────────────────────────────────────────────────────┘
             │
             │ A2A Protocol (HTTP/JSON)
             │ Agent-to-Agent Remote Skills
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                     REMOTE A2A AGENTS                           │
│                                                                 │
│   ┌─────────────────┐           ┌─────────────────┐           │
│   │  Google Agent   │           │   Meta Agent    │           │
│   │  (port 8003)    │           │  (port 8004)    │           │
│   │                 │           │                 │           │
│   │ • Scale calc    │           │ • Infra design  │           │
│   │ • Distributed   │           │ • News feed     │           │
│   │   systems       │           │   architecture  │           │
│   └─────────────────┘           └─────────────────┘           │
└─────────────────────────────────────────────────────────────────┘
```

### Interview Flow

```
1. User starts interview → Frontend creates DB record
2. WebSocket connects → Orchestrator starts ADK session (InMemory)
3. Routing agent → Determines company/type
4. Intro agent → Collects candidate info
5. Interview agent → Conducts technical interview
   ├─ Design agent (system design)
   │  └─ Calls remote agents (Google/Meta) via A2A
   └─ Coding agent (coding interview)
6. Closing agent → Wraps up session
7. WebSocket disconnect → Syncs session to PostgreSQL
8. Recording uploaded → Saved to Vercel Blob
```

---

## ✅ Implemented Features

### Core Platform
- **Multi-agent orchestration** using Google ADK
  - Phase-based routing (routing → intro → interview → closing)
  - State management with session persistence
  - InMemory sessions for real-time performance, synced to PostgreSQL on completion
- **Real-time audio** with Gemini 2.5 Flash Native Audio
  - Bidirectional streaming (PCM 16kHz → 24kHz)
  - Barge-in support (interruption handling)
  - Speech-to-text and text-to-speech
- **Canvas collaboration** with Excalidraw
  - Real-time drawing for system design diagrams
  - State persistence to PostgreSQL
  - Screenshot capture (every 30s sent to orchestrator)
- **Recording & persistence**
  - Composite video (canvas + webcam + UI) via MediaRecorder
  - Upload to Vercel Blob storage
  - Transcription persistence in ADK database

### Interview Types
- **System Design** (fully implemented)
  - Remote agent evaluation via A2A protocol
  - Company-specific feedback (Google, Meta agents)
  - Canvas-based diagramming
- **Coding** (agent implemented, UI pending)
  - Basic coding agent structure
  - Code execution not yet integrated

### Infrastructure
- **Authentication**: Better-Auth with GitHub/Google OAuth
- **Database**: PostgreSQL with Drizzle ORM
  - Interviews table (basic metadata, video URL)
  - Canvas state table (Excalidraw elements/appState)
  - ADK session tables (transcriptions, events)
- **Storage**: Vercel Blob (video recordings)
- **WebSocket**: FastAPI + Uvicorn (bidirectional streaming)

---

## 🛠️ Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS |
| Backend | Python 3.14, FastAPI, Google ADK 1.16.0 |
| AI | Gemini 2.5 Flash Native Audio |
| Database | PostgreSQL, Drizzle ORM |
| Auth | Better-Auth |
| Storage | Vercel Blob |
| Canvas | Excalidraw |

---

## 📁 Project Structure

```
interview-agent/
├── services/
│   ├── frontend/                    # Next.js app
│   │   ├── app/
│   │   │   ├── interview/[interviewId]/system-design/  # Interview UI
│   │   │   └── api/interviews/[id]/upload-recording/   # Recording upload
│   │   ├── modules/
│   │   │   ├── interview/           # Interview components & hooks
│   │   │   │   ├── common/hooks/    # Audio worklets, recording, WebSocket
│   │   │   │   └── system-design/   # System design interview UI
│   │   │   └── home/                # Home page (company selection)
│   │   ├── db/schema/               # Database schema
│   │   │   ├── interviews.ts        # Interview records
│   │   │   ├── canvas.ts            # Canvas state
│   │   │   └── users.ts             # Better-Auth
│   │   └── public/
│   │       ├── audio-player-worklet.js   # 24kHz playback
│   │       └── audio-recorder-worklet.js # 16kHz recording
│   │
│   ├── interview-orchestrator/      # Python ADK service
│   │   └── interview_orchestrator/
│   │       ├── server.py            # WebSocket server
│   │       ├── root_agent.py        # Root coordinator
│   │       ├── agents/              # Phase agents
│   │       │   ├── routing.py
│   │       │   ├── intro.py
│   │       │   ├── interview.py     # Interview coordinator
│   │       │   ├── closing.py
│   │       │   └── interview_types/
│   │       │       ├── design.py    # System design agent
│   │       │       └── coding.py    # Coding agent
│   │       └── shared/
│   │           ├── agent_registry.py  # A2A remote agent discovery
│   │           ├── prompts/           # Agent instructions
│   │           └── schemas/           # Data models
│   │
│   ├── google-agent/                # Google A2A remote agent
│   │   └── agent.py                 # Scale calc, distributed systems
│   │
│   └── meta-agent/                  # Meta A2A remote agent
│       └── agent.py                 # Infrastructure, news feed
│
├── README.md
└── TODO.md                          # Roadmap for pending features
```

---

## 🚀 Quick Start

### Prerequisites
- Node.js 20+
- Python 3.14+
- PostgreSQL
- Google API Key (Gemini)

### 1. Frontend Setup

```bash
cd services/frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Required: DATABASE_URL, GOOGLE_API_KEY, BLOB_READ_WRITE_TOKEN, Better-Auth OAuth

# Run migrations
npx drizzle-kit push

# Start development server
npm run dev
```

**Frontend**: http://localhost:3000

### 2. Orchestrator Setup

```bash
cd services/interview-orchestrator

# Create virtual environment
uv venv && source .venv/bin/activate

# Install dependencies
uv pip install -e .

# Configure environment
cp .env.example .env
# Required: GOOGLE_API_KEY, DATABASE_URL

# Start server
python -m uvicorn interview_orchestrator.server:app --host 0.0.0.0 --port 8000 --reload
```

**Orchestrator**: http://localhost:8000

### 3. Remote Agents (Optional - for company-specific evaluation)

**Google Agent:**
```bash
cd services/google-agent
uv venv && source .venv/bin/activate
uv pip install -e .
cp .env.example .env  # Add GOOGLE_API_KEY
uvicorn agent:a2a_app --host localhost --port 8003
```

**Meta Agent:**
```bash
cd services/meta-agent
uv venv && source .venv/bin/activate
uv pip install -e .
cp .env.example .env  # Add GOOGLE_API_KEY
uvicorn agent:a2a_app --host localhost --port 8004
```

**Configure orchestrator to use remote agents:**
```bash
# In services/interview-orchestrator/.env
INTERVIEW_AGENTS=google,meta
GOOGLE_AGENT_URL=http://localhost:8003
GOOGLE_AGENT_TYPES=system_design,coding
META_AGENT_URL=http://localhost:8004
META_AGENT_TYPES=system_design
```

### 4. Start Interview

1. Visit http://localhost:3000
2. Sign in (GitHub/Google)
3. Select company card and click "Start Interview"
4. Grant microphone permissions
5. Start practicing!

---

## 🔑 Key Implementation Details

### Audio Processing
- **Frontend**: AudioWorklet processors for recording (16kHz) and playback (24kHz)
- **Transmission**: Base64-encoded PCM chunks via WebSocket
- **Orchestrator**: Gemini Live API handles bidirectional streaming
- **Barge-in**: Interruptions handled by ADK event system

### Session Management
- **InMemory sessions** during interview (zero latency)
- **PostgreSQL sync** on disconnect (filtered to text transcriptions only)
- **Canvas state** persisted separately for instant saves
- **Video recording** uploaded to Vercel Blob on interview end

### Multi-Agent Coordination
- **Phase-based routing** using session state (`interview_phase`)
- **Sub-agent transfers** via ADK agent hierarchy
- **State propagation** through `ctx.session.state`
- **Remote agents** consumed as tools via A2A protocol
