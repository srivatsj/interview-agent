# Interview Agent Frontend

Next.js 16 application with real-time audio streaming, dual canvas system (Excalidraw + Monaco), video recording, and Better-Auth integration. Connects to interview-orchestrator via WebSocket for AI-powered technical interviews.

## Architecture

```
Browser
  ├── Audio Pipeline: Mic (16kHz) → WebSocket → Backend
  │                   Speaker ← (24kHz) ← WebSocket ← Agent
  ├── Canvas: Excalidraw (whiteboard) + Monaco (code editor)
  ├── Recording: Canvas + Webcam → Composite → MediaRecorder → Blob
  └── WebSocket: ws://localhost:8000/ws/{userId}?interview_id={id}
```

### Key Features

**Real-time Audio**
- AudioWorklet processors (16kHz recording, 24kHz playback)
- Voice Activity Detection (VAD) for barge-in
- Audio mixing (mic + agent) for recording
- Low-latency bidirectional streaming

**Dual Canvas System**
- Excalidraw: Whiteboard for system design diagrams
- Monaco: Code editor with multi-language support
- Tabbed UI (switch between whiteboard/code)
- Canvas stream capture for video recording

**Recording Pipeline**
- Canvas capture (30 FPS)
- Webcam feed (Picture-in-Picture)
- Composite video (1920x1080)
- Mixed audio (mic + agent)
- Upload to Vercel Blob

**Authentication**
- Better-Auth with social providers (GitHub, Google)
- Email/password authentication
- Session management with PostgreSQL

**Payment (AP2)**
- Stripe integration with payment methods
- Cart mandate handling
- Payment confirmation UI
- Transaction persistence

## Setup

### Install
```bash
cd services/frontend
npm install
```

### Configure
```bash
cp .env.example .env
```

**Required Variables:**
```bash
# Database
DATABASE_URL=postgresql://localhost:5432/interview_db

# Auth (Better-Auth)
BETTER_AUTH_SECRET=your_secret_here
BETTER_AUTH_URL=http://localhost:3000

# OAuth Providers
GITHUB_CLIENT_ID=your_github_client_id
GITHUB_CLIENT_SECRET=your_github_client_secret
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret

# Storage
BLOB_READ_WRITE_TOKEN=vercel_blob_token

# Stripe (for payments)
STRIPE_SECRET_KEY=sk_test_...
STRIPE_PUBLISHABLE_KEY=pk_test_...
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=pk_test_...
```

### Database
```bash
npm run db:generate  # Generate migrations from schema
npm run db:push      # Push schema to database (or: npm run db)
```

### Run
```bash
npm run dev
```

**Visit**: http://localhost:3000

### Lint
```bash
npm run lint
npm run format  # Prettier
```

## Code Structure

```
services/frontend/
├── app/                          # Next.js App Router
│   ├── (auth)/                  # Auth routes
│   │   ├── sign-in/page.tsx
│   │   └── sign-up/page.tsx
│   ├── (dashboard)/             # Protected routes
│   │   ├── dashboard/page.tsx
│   │   ├── interviews/page.tsx
│   │   └── settings/payment/page.tsx
│   ├── interview-session/       # Interview UI
│   │   ├── new/page.tsx
│   │   └── [interviewId]/page.tsx
│   └── api/                     # API routes
│       ├── [...all]/route.ts   # Better-Auth handler
│       ├── interviews/[id]/upload-recording/route.ts
│       └── payments/
│           ├── get-token/route.ts
│           └── execute/route.ts
├── modules/                      # Feature modules
│   ├── interview/               # Interview module
│   │   ├── common/
│   │   │   ├── hooks/          # Audio, WebSocket, recording
│   │   │   ├── ui/components/  # Interview components
│   │   │   └── utils/          # Helpers
│   │   ├── system-design/      # Excalidraw integration
│   │   └── coding/             # Monaco editor integration
│   ├── home/                    # Dashboard
│   ├── auth/                    # Auth views
│   └── payments/                # Payment settings
├── db/                          # Database layer
│   ├── schema/
│   │   ├── namespaces.ts       # PostgreSQL schemas
│   │   ├── users.ts            # Better-Auth tables
│   │   ├── interviews.ts       # Interview records
│   │   ├── canvas.ts           # Canvas state
│   │   └── payments.ts         # Stripe integration
│   └── index.ts                 # Drizzle client
└── public/
    ├── audio-player-worklet.js  # 24kHz playback
    └── audio-recorder-worklet.js # 16kHz recording + VAD
```

## Audio System

### AudioWorklet Architecture

**Recorder** (public/audio-recorder-worklet.js):
- Records microphone at 16kHz
- Voice Activity Detection (VAD)
- Energy threshold: 0.05
- Speech duration: 0.5s minimum
- Triggers `speech_start` event for barge-in
- Converts Float32 → Int16 PCM

**Player** (public/audio-player-worklet.js):
- Plays agent audio at 24kHz
- Queue-based buffering
- Flush support (interruption)
- Converts Int16 PCM → Float32

### Audio Hooks

**useAudioWorkletRecorder**:
```typescript
startRecording(stream)  // Start recording from mic
stopRecording()         // Stop and cleanup
// Callbacks: onAudioData(base64), onSpeechStart()
```

**useAudioWorkletPlayer**:
```typescript
initializePlayer()      // Setup AudioContext
playAudio(base64)       // Play PCM chunk
flush()                 // Clear buffer (barge-in)
getAudioStream()        // Get MediaStream for recording
```

**useAudioMixer**:
```typescript
createMixedStream(micStream, agentStream)  // Mix for recording
addAgentAudio(stream)                      // Update agent audio
cleanup()
```

## WebSocket Integration

**Hook**: `useWebSocket`

**Endpoint**: `ws://localhost:8000/ws/{userId}?interview_id={id}&is_audio=true`

**Outgoing Messages**:
```typescript
// Audio chunk (16kHz PCM)
{ mime_type: "audio/pcm", data: "base64..." }

// Text message
{ mime_type: "text/plain", data: "Hello" }

// Payment confirmation
{ mime_type: "confirmation_response", data: { confirmation_id, approved } }

// Canvas screenshot (every 30s)
{ mime_type: "image/png", data: "base64..." }
```

**Incoming Messages**:
```typescript
{
  author: "agent",
  is_partial: boolean,
  turn_complete: boolean,
  interrupted: boolean,
  parts: [
    { type: "audio/pcm", data: "base64..." },
    { type: "text", data: "Welcome..." }
  ],
  state: {
    interview_phase: "intro",
    routing_decision: { company, interview_type },
    candidate_info: { name, years_experience, ... }
  }
}
```

## Canvas System

### Excalidraw (Whiteboard)

**Component**: `modules/interview/system-design/ui/components/excalidraw-canvas.tsx`

**Features**:
- Dynamic import (no SSR)
- Light theme
- Imperative API via callback
- State persistence (elements + appState)

**Hooks**:
- `useCanvasStream`: Capture canvas as MediaStream (30 FPS)
- `useCanvasScreenshot`: Periodic snapshots (every 30s) → WebSocket

### Monaco (Code Editor)

**Component**: `modules/interview/coding/ui/components/code-editor-canvas.tsx`

**Features**:
- Multi-language support (JavaScript, Python, Java, etc.)
- Syntax highlighting
- IntelliSense
- Read-only mode for completed interviews
- State persistence (code + language)

## Recording System

**Pipeline**:
```
1. Canvas Stream (30 FPS) → useCanvasStream
2. Webcam Stream → getUserMedia
3. Composite Video → useCompositeVideo (canvas + webcam PiP)
4. Mixed Audio → useAudioMixer (mic + agent)
5. Recording → useScreenRecorder (MediaRecorder, VP9 + Opus)
6. Upload → useRecordingUpload (Vercel Blob)
```

**Composite Layout** (useCompositeVideo):
- Canvas: Full frame (1920x1080)
- Webcam: Picture-in-Picture (320x240, bottom-right)
- Border: 2px white with shadow

**Video Format**:
- Codec: VP9 + Opus
- Bitrate: 2.5 Mbps
- Container: WebM
- Chunk interval: 1000ms

## Database Schema

**Namespaces**:
- `auth`: Better-Auth tables (user, session, account, verification)
- `product`: Application tables (interviews, canvas_state, payments)

**Interviews** (product.interviews):
```typescript
{
  id: uuid,
  role: text,              // "Backend Engineer"
  level: text,             // "Senior"
  status: text,            // "in_progress" | "completed"
  videoUrl: text,          // Vercel Blob URL
  durationSeconds: integer,
  createdAt: timestamp,
  completedAt: timestamp
}
```

**Canvas State** (product.canvas_state):
```typescript
{
  id: uuid,
  interviewId: uuid,
  elements: jsonb,  // [{ type: "excalidraw", elements }, { type: "code", code, language }]
  appState: jsonb,  // { excalidraw: {...}, codeLanguage: "javascript" }
  createdAt: timestamp
}
```

**Payment Methods** (product.user_payment_methods):
```typescript
{
  id: uuid,
  userId: text,
  stripeCustomerId: text,
  defaultPaymentMethodId: text,
  cardLast4: text,
  cardBrand: text,
  createdAt: timestamp
}
```

## API Routes

**Auth**: `/api/[...all]`
- Better-Auth handler (sign-in, sign-up, session, OAuth callbacks)

**Recording Upload**: `POST /api/interviews/[id]/upload-recording`
- Upload video to Vercel Blob
- Update interview status to "completed"
- Returns: `{ url, interviewId }`

**Payment Token**: `POST /api/payments/get-token`
- Returns encrypted payment method token for AP2
- Body: `{ user_id }`

**Payment Execute**: `POST /api/payments/execute`
- Processes AP2 payment mandate via Stripe
- Creates PaymentIntent and confirms charge
- Stores transaction in `ap2_transactions`
- Returns payment receipt

## Inter-Service Communication

**With Orchestrator**:
- WebSocket: Bidirectional audio/text streaming
- Connection: `ws://localhost:8000/ws/{userId}?interview_id={id}`
- Messages: Audio PCM, text, payment confirmations, canvas screenshots

**With Vercel Blob**:
- Recording upload via `@vercel/blob`
- PUT request with video file
- Returns public URL

**With Stripe**:
- PaymentIntent creation
- Charge confirmation (off_session)
- Payment method storage

## Environment Namespaces

PostgreSQL schemas for logical separation:
- `auth.*`: Better-Auth tables (user, session, account, verification)
- `product.*`: Application tables (interviews, canvas, payments)

Configured in `db/schema/namespaces.ts`:
```typescript
export const auth = pgSchema("auth")
export const product = pgSchema("product")
```
