# Interview Agent Platform

> **AI-Powered Technical Interview Platform** with real-time audio/video, canvas collaboration, and multi-agent orchestration using Google ADK.

An intelligent interview platform that provides realistic practice for system design and coding interviews with AI agents specialized for different companies (Google, Meta, etc.).

---

## 🏗️ High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    FRONTEND (Next.js 16)                        │
│                     http://localhost:3000                        │
│                                                                  │
│  ┌────────────────┐  ┌──────────────┐  ┌──────────────────┐   │
│  │  Interview UI  │  │   Excalidraw │  │  Video/Audio      │   │
│  │  (React 19)    │  │   Canvas     │  │  (WebRTC)         │   │
│  └────────┬───────┘  └──────┬───────┘  └─────────┬────────┘   │
│           │                  │                     │             │
│           └──────────────────┴─────────────────────┘             │
│                              │                                   │
└──────────────────────────────┼───────────────────────────────────┘
                               │
                               │ WebSocket (Audio PCM + Canvas Screenshots)
                               │ ws://localhost:8000/ws/{interviewId}
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│           INTERVIEW ORCHESTRATOR (Python + Google ADK)          │
│                     http://localhost:8000                        │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              Root Coordinator Agent                       │  │
│  │         (Manages Multi-Phase Interview Flow)              │  │
│  └──────────────────────┬───────────────────────────────────┘  │
│                         │                                       │
│         ┌───────────────┼───────────────┐                      │
│         ▼               ▼               ▼                      │
│  ┌─────────────┐ ┌────────────┐ ┌────────────┐               │
│  │   Routing   │ │   Intro    │ │  Closing   │               │
│  │   Agent     │ │   Agent    │ │   Agent    │               │
│  └─────────────┘ └────────────┘ └────────────┘               │
│                         │                                       │
│              ┌──────────┴──────────┐                           │
│              ▼                     ▼                           │
│      ┌────────────┐         ┌──────────────┐                  │
│      │   Coding   │         │ System Design│                  │
│      │   Agent    │         │   Agent      │                  │
│      └────────────┘         └──────┬───────┘                  │
│                                    │                           │
└────────────────────────────────────┼───────────────────────────┘
                                     │
                                     │ A2A Protocol (HTTP/JSON)
                                     │ Remote Agent Skill Consumption
                                     ▼
          ┌─────────────────────────────────────────────┐
          │         REMOTE A2A AGENTS                   │
          │                                             │
          │  ┌────────────────┐  ┌────────────────┐   │
          │  │ Google Agent   │  │  Meta Agent    │   │
          │  │ (port 8003)    │  │  (port 8004)   │   │
          │  │                │  │                │   │
          │  │ Skills:        │  │ Skills:        │   │
          │  │ - Scale Calc   │  │ - Infra Design │   │
          │  │ - Distributed  │  │ - News Feed    │   │
          │  └────────────────┘  └────────────────┘   │
          └─────────────────────────────────────────────┘
```

---

## 📊 End-to-End Flow

### 1. **Interview Creation**
```
User clicks "Start Interview"
    ↓
Frontend: POST /interview/new?company=google&type=system_design
    ↓
Server Action: createInterview() → Creates DB record with UUID
    ↓
Redirect to: /interview/{uuid}/system-design
```

### 2. **Interview Session Initialization**
```
Frontend: SystemDesignInterview component loads
    ↓
1. Validate interview exists (validateInterviewExists)
2. Initialize AudioWorklet player (24kHz PCM)
3. Get microphone stream (getUserMedia)
4. Initialize AudioWorklet recorder (16kHz PCM)
5. Capture canvas stream (canvas.captureStream)
6. Mix audio streams (candidate mic + AI audio)
7. Start screen recording (MediaRecorder)
8. Connect WebSocket to orchestrator
    ↓
WebSocket: ws://localhost:8000/ws/{uuid}?is_audio=true
```

### 3. **Real-Time Interview Flow**
```
┌─────────────┐                 ┌──────────────────┐                ┌─────────────┐
│  Frontend   │                 │  Orchestrator    │                │ Remote A2A  │
└──────┬──────┘                 └────────┬─────────┘                └──────┬──────┘
       │                                 │                                  │
       │ WebSocket Connect               │                                  │
       │─────────────────────────────────>                                  │
       │                                 │                                  │
       │                         routing_agent activates                    │
       │<─────────────────────────────────                                  │
       │ "Which company?"                │                                  │
       │                                 │                                  │
       │ audio/pcm (candidate voice)     │                                  │
       │─────────────────────────────────>                                  │
       │                                 │                                  │
       │                         Speech-to-text → "Google system design"    │
       │                                 │                                  │
       │<─────────────────────────────────                                  │
       │ audio/pcm (AI response)         │                                  │
       │                                 │                                  │
       │                         Transfer to intro_agent                    │
       │<─────────────────────────────────                                  │
       │ "Tell me about yourself"        │                                  │
       │                                 │                                  │
       │ audio/pcm (candidate response)  │                                  │
       │─────────────────────────────────>                                  │
       │                                 │                                  │
       │                         save_candidate_info()                      │
       │                         Transfer to interview_agent                │
       │                                 │                                  │
       │<─────────────────────────────────                                  │
       │ "Design WhatsApp"               │                                  │
       │                                 │                                  │
       │ image/png (canvas screenshot)   │                                  │
       │─────────────────────────────────> Receives canvas every 30s        │
       │                                 │                                  │
       │                                 │ A2A Request: analyze_scale       │
       │                                 │─────────────────────────────────>│
       │                                 │                                  │
       │                                 │<─────────────────────────────────│
       │                                 │ Scale calculation results        │
       │                                 │                                  │
       │<─────────────────────────────────                                  │
       │ audio/pcm + text feedback       │                                  │
       │                                 │                                  │
       │ Candidate draws on canvas       │                                  │
       │ (recorded via canvas.captureStream)                               │
       │                                 │                                  │
       │ Click "End Interview"           │                                  │
       │─────────────────────────────────>                                  │
       │                                 │                                  │
       │ WebSocket disconnect            │                                  │
       │ Stop recording                  │                                  │
       │ Upload recording to Vercel Blob │                                  │
       │ POST /api/interviews/{uuid}/upload-recording                       │
       │                                 │                                  │
       │ Update DB: status=completed, videoUrl, completedAt                 │
       │                                 │                                  │
       │ Redirect to /                   │                                  │
       └─────────────────────────────────┴──────────────────────────────────┘
```

### 4. **Data Flow Details**

**Frontend → Orchestrator:**
- **Audio**: PCM 16kHz base64-encoded chunks via WebSocket
- **Canvas**: PNG screenshots every 30 seconds via WebSocket
- **Format**: `{ mime_type: 'audio/pcm', data: 'base64...' }`

**Orchestrator → Frontend:**
- **Audio**: PCM 24kHz base64-encoded from Gemini Live API
- **Text**: Transcriptions (input/output) for debugging
- **Format**: `{ author, is_partial, turn_complete, interrupted, parts: [...] }`

**Orchestrator → Remote Agents:**
- **Protocol**: A2A (Agent-to-Agent) via HTTP/JSON
- **Skills**: Function calls with parameters
- **Returns**: Structured results (scale calculations, design recommendations)

---

## 🎯 Currently Implemented Features

### ✅ Frontend (Next.js 16 + React 19)

**Interview Management:**
- [x] Interview creation with UUID tracking
- [x] Server Actions for database operations
- [x] Validation for interview existence
- [x] Prevention of duplicate interviews (React Strict Mode handling)

**Real-Time Communication:**
- [x] WebSocket connection with auto-reconnect
- [x] Bidirectional audio streaming (PCM format)
- [x] Canvas screenshot transmission (every 30s)
- [x] Structured event handling (interruption, turn completion)

**Audio/Video Recording:**
- [x] AudioWorklet-based recording (16kHz PCM)
- [x] AudioWorklet-based playback (24kHz PCM)
- [x] Audio mixing (candidate mic + AI audio)
- [x] Canvas stream capture (30 FPS)
- [x] Screen recording with MediaRecorder
- [x] Recording upload to Vercel Blob
- [x] Database persistence (videoUrl, status, timestamps)

**User Interface:**
- [x] Excalidraw canvas for system design diagrams
- [x] Split panel layout (canvas + video)
- [x] Webcam feed display
- [x] AI avatar placeholder
- [x] Interview timer
- [x] End interview button with loading state
- [x] Connection status indicators

**Authentication & Authorization:**
- [x] Better-Auth integration
- [x] GitHub OAuth
- [x] Google OAuth
- [x] Protected routes
- [x] Session management

### ✅ Orchestrator (Python + Google ADK)

**Multi-Agent Coordination:**
- [x] Root coordinator agent
- [x] Routing agent (determines interview type)
- [x] Intro agent (candidate information collection)
- [x] Interview agent (conducts technical interview)
- [x] Closing agent (wraps up session)
- [x] Agent transfer mechanism

**Audio Processing:**
- [x] Gemini 2.5 Flash Native Audio integration
- [x] Real-time bidirectional streaming
- [x] Speech-to-text (input transcription)
- [x] Text-to-speech (output audio)
- [x] Barge-in support (interruption handling)

**A2A Protocol:**
- [x] Remote agent discovery
- [x] Skill consumption from Google Agent
- [x] Skill consumption from Meta Agent
- [x] HTTP/JSON communication
- [x] Dynamic agent registration

**WebSocket Server:**
- [x] FastAPI + Uvicorn
- [x] Client connection management
- [x] Concurrent bidirectional messaging
- [x] Error handling and reconnection
- [x] UUID-based session tracking

### ✅ Remote Agents (A2A Protocol)

**Google Agent (port 8003):**
- [x] Scale requirement analysis skill
- [x] Distributed systems design skill
- [x] Massive-scale calculations (QPS, storage, bandwidth)
- [x] Consistency models recommendations
- [x] Sharding strategies

**Meta Agent (port 8004):**
- [x] Infrastructure design skill
- [x] News feed architecture skill
- [x] CDN and edge caching recommendations
- [x] Multi-region deployment strategies

### ✅ Database & Storage

**PostgreSQL + Drizzle ORM:**
- [x] Interviews table (id, role, level, status, videoUrl, timestamps)
- [x] Users table (Better-Auth schema)
- [x] UUID primary keys
- [x] Migration support

**Vercel Blob Storage:**
- [x] Video recording upload
- [x] Public URL generation
- [x] File naming convention (`recordings/{uuid}.webm`)

---

## 🛠️ Tech Stack

### Frontend
- **Framework**: Next.js 16 (App Router) + React 19
- **Language**: TypeScript
- **Styling**: Tailwind CSS + shadcn/ui
- **Auth**: Better-Auth (GitHub, Google OAuth)
- **Database**: PostgreSQL + Drizzle ORM
- **Storage**: Vercel Blob
- **Canvas**: Excalidraw
- **Audio**: Web Audio API + AudioWorklet

### Backend (Orchestrator)
- **Framework**: FastAPI + Uvicorn
- **Language**: Python 3.14
- **AI**: Google ADK 1.16.0
- **Model**: Gemini 2.5 Flash Native Audio
- **Protocol**: WebSocket (bidirectional streaming)

### Remote Agents
- **Framework**: Google ADK (A2A Protocol)
- **Language**: Python 3.14
- **Skills**: Custom function tools
- **Deployment**: Standalone services (ports 8003, 8004)

---

## 📁 Project Structure

```
interview-agent/
├── services/
│   ├── frontend/                        # Next.js frontend
│   │   ├── app/
│   │   │   ├── (auth)/                  # Auth pages
│   │   │   ├── (dashboard)/             # Dashboard layout
│   │   │   ├── interview/
│   │   │   │   ├── new/                 # Interview creation
│   │   │   │   └── [interviewId]/
│   │   │   │       └── system-design/   # Interview UI
│   │   │   └── api/
│   │   │       └── interviews/
│   │   │           └── [id]/
│   │   │               └── upload-recording/  # Recording upload API
│   │   ├── modules/
│   │   │   ├── interview/
│   │   │   │   ├── actions.ts           # Server actions
│   │   │   │   ├── common/
│   │   │   │   │   ├── hooks/           # Shared hooks
│   │   │   │   │   │   ├── use-audio-worklet-player.ts
│   │   │   │   │   │   ├── use-audio-worklet-recorder.ts
│   │   │   │   │   │   ├── use-audio-mixer.ts
│   │   │   │   │   │   ├── use-screen-recorder.ts
│   │   │   │   │   │   ├── use-canvas-stream.ts
│   │   │   │   │   │   ├── use-recording-upload.ts
│   │   │   │   │   │   ├── use-canvas-screenshot.ts
│   │   │   │   │   │   └── use-websocket.ts
│   │   │   │   │   └── ui/              # Shared components
│   │   │   │   └── system-design/
│   │   │   │       └── ui/
│   │   │   │           ├── components/  # Excalidraw
│   │   │   │           └── views/       # Main interview view
│   │   │   ├── home/                    # Home page
│   │   │   └── auth/                    # Auth views
│   │   ├── db/
│   │   │   └── schema/
│   │   │       └── interviews.ts        # Database schema
│   │   └── public/
│   │       ├── audio-player-worklet.js  # Audio playback processor
│   │       └── audio-recorder-worklet.js # Audio recording processor
│   │
│   ├── interview-orchestrator/          # Python orchestrator
│   │   ├── interview_orchestrator/
│   │   │   ├── server.py                # WebSocket server
│   │   │   ├── root_agent.py            # Root coordinator
│   │   │   ├── agents/
│   │   │   │   ├── routing.py           # Routing agent
│   │   │   │   ├── intro.py             # Intro agent
│   │   │   │   ├── interview.py         # Interview coordinator
│   │   │   │   ├── closing.py           # Closing agent
│   │   │   │   └── interview_types/
│   │   │   │       ├── coding.py        # Coding interview
│   │   │   │       └── design.py        # System design interview
│   │   │   └── shared/
│   │   │       ├── schemas/             # Data models
│   │   │       ├── prompts/             # Agent prompts
│   │   │       └── agent_registry.py    # A2A agent discovery
│   │   └── pyproject.toml
│   │
│   ├── google-agent/                    # Google A2A agent
│   │   ├── agent.py                     # Scale + distributed systems skills
│   │   └── pyproject.toml
│   │
│   └── meta-agent/                      # Meta A2A agent
│       ├── agent.py                     # Infrastructure + news feed skills
│       └── pyproject.toml
│
├── README.md                            # This file
└── TODO.md                              # Implementation roadmap
```

---

## 🚀 Getting Started

### Prerequisites
- **Node.js** 20+ (for frontend)
- **Python** 3.14+ (for orchestrator and agents)
- **PostgreSQL** (for database)
- **Google API Key** (for Gemini models)

### 1. Clone Repository
```bash
git clone <repository-url>
cd interview-agent
```

### 2. Setup Frontend
```bash
cd services/frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env and add:
# - DATABASE_URL (PostgreSQL connection string)
# - GOOGLE_API_KEY
# - BLOB_READ_WRITE_TOKEN (Vercel Blob)
# - Better-Auth OAuth credentials

# Run database migrations
npx drizzle-kit push

# Start development server
npm run dev
```

Frontend will be available at: **http://localhost:3000**

### 3. Setup Interview Orchestrator
```bash
cd services/interview-orchestrator

# Create virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv pip install -e .

# Configure environment
cp .env.example .env
# Edit .env and add:
# - GOOGLE_API_KEY

# Start orchestrator
python -m uvicorn interview_orchestrator.server:app --host 0.0.0.0 --port 8000 --reload
```

Orchestrator will be available at: **http://localhost:8000**

### 4. Setup Remote Agents (Optional)

**Google Agent:**
```bash
cd services/google-agent
uv venv
source .venv/bin/activate
uv pip install -e .
cp .env.example .env  # Add GOOGLE_API_KEY

# Start agent
uvicorn agent:a2a_app --host localhost --port 8003
```

**Meta Agent:**
```bash
cd services/meta-agent
uv venv
source .venv/bin/activate
uv pip install -e .
cp .env.example .env  # Add GOOGLE_API_KEY

# Start agent
uvicorn agent:a2a_app --host localhost --port 8004
```

### 5. Start Interview

1. Navigate to **http://localhost:3000**
2. Sign in with GitHub or Google
3. Click "Start Interview" on a company card
4. Grant microphone permissions
5. Start practicing!

---

## 🔧 Development

### Running Tests

**Frontend:**
```bash
cd services/frontend
npm run test
npm run lint
```

**Orchestrator:**
```bash
cd services/interview-orchestrator
uv run pytest
uv run ruff check .
```

### Code Formatting

**Frontend:**
```bash
npm run format
```

**Python:**
```bash
uv run ruff format .
uv run ruff check . --fix
```

---

## 🐛 Troubleshooting

### Issue: "Invalid interview ID" alert
**Cause**: Navigating directly to interview page without creating a record.
**Fix**: Always start interviews from the home page by clicking "Start Interview".

### Issue: No audio from AI
**Cause**: Orchestrator not running or WebSocket disconnected.
**Fix**:
1. Verify orchestrator is running on port 8000
2. Check browser console for WebSocket errors
3. Ensure `GOOGLE_API_KEY` is set in orchestrator .env

### Issue: Recording upload fails
**Cause**: Invalid `BLOB_READ_WRITE_TOKEN` or interview ID mismatch.
**Fix**:
1. Verify Vercel Blob token in frontend .env
2. Check that interview was created properly (UUID format)
3. Check browser network tab for error details

### Issue: Canvas not captured in recording
**Cause**: Canvas stream not ready when recording started.
**Fix**: Already handled with 2-second delay. If still failing, check browser console for canvas capture errors.

---

## 📝 License

[Add your license here]

---

## 🤝 Contributing

[Add contributing guidelines here]

---

## 📧 Contact

[Add contact information here]
