# Frontend - Agent Documentation

Quick reference for AI coding agents to understand the frontend codebase.

## Core Architecture

**Type**: Next.js 16 App Router with React 19
**Framework**: Next.js + TypeScript + Tailwind CSS
**Database**: PostgreSQL with Drizzle ORM
**Auth**: Better-Auth
**Storage**: Vercel Blob

## Entry Points

1. **app/page.tsx** - Landing page
2. **app/(dashboard)/dashboard/page.tsx** - Home dashboard
3. **app/interview-session/[interviewId]/page.tsx** - Active interview UI
4. **app/api/[...all]/route.ts** - Better-Auth handler

## Key React Components

### Interview UI
**modules/interview/common/ui/views/unified-interview.tsx:45** - Main interview interface
- Tabbed layout (Whiteboard | Code Editor)
- Resizable panels (canvas 70% | video 30%)
- Video panel with webcam + AI avatar

**modules/interview/system-design/ui/components/excalidraw-canvas.tsx:20** - Whiteboard
- Dynamic import (no SSR)
- Canvas stream capture for recording
- State persistence

**modules/interview/coding/ui/components/code-editor-canvas.tsx:28** - Code editor
- Monaco Editor integration
- Multi-language support
- State persistence

### Audio Components
**public/audio-recorder-worklet.js:10** - AudioWorkletProcessor
- 16kHz recording
- VAD (energy threshold: 0.05, speech duration: 0.5s)
- Float32 → Int16 PCM conversion

**public/audio-player-worklet.js:10** - AudioWorkletProcessor
- 24kHz playback
- Queue buffering
- Flush support (barge-in)
- Int16 → Float32 PCM conversion

## Critical Hooks

### Audio Hooks
**modules/interview/common/hooks/use-audio-worklet-recorder.ts:23**
```typescript
startRecording(stream)  // Start mic recording
stopRecording()         // Stop and cleanup
// Callbacks: onAudioData(base64PCM), onSpeechStart()
```

**modules/interview/common/hooks/use-audio-worklet-player.ts:28**
```typescript
initializePlayer()      // Create AudioContext + worklet
playAudio(base64)       // Play PCM chunk
flush()                 // Clear buffer (interruption)
getAudioStream()        // MediaStream for recording
```

**modules/interview/common/hooks/use-audio-mixer.ts:18**
```typescript
createMixedStream(micStream, agentStream)
addAgentAudio(stream)
cleanup()
```

### WebSocket Hook
**modules/interview/common/hooks/use-websocket.ts:45**
```typescript
const { isConnected, sendMessage, connect, disconnect } = useWebSocket({
  url: `ws://localhost:8000/ws/${userId}?interview_id=${id}&is_audio=true`,
  onMessage: handleAgentEvent,
  onStateUpdate: handleStateUpdate,
  autoConnect: false
})

// Send message
sendMessage({ mime_type: "audio/pcm" | "text/plain", data: ... })
```

**Message Types**:
- Outgoing: `audio/pcm`, `text/plain`, `image/png`, `confirmation_response`
- Incoming: Structured agent events with `parts[]` and `state`

### Recording Hooks
**modules/interview/common/hooks/use-canvas-stream.ts:15**
- Captures Excalidraw canvas as MediaStream (30 FPS)
- Retry logic (5 attempts, 1.5s initial delay)

**modules/interview/common/hooks/use-composite-video.ts:23**
- Composites canvas + webcam (PiP layout)
- 1920x1080 canvas, 320x240 webcam (bottom-right)

**modules/interview/common/hooks/use-screen-recorder.ts:28**
- MediaRecorder with VP9 + Opus
- Bitrate: 2.5 Mbps
- Methods: `startRecording(audioStream, videoStream)`, `stopRecording()`

**modules/interview/common/hooks/use-recording-upload.ts:18**
- Uploads to `/api/interviews/${id}/upload-recording`
- Returns upload progress

## Database Schema

**Location**: `db/schema/`

**Namespaces** (namespaces.ts):
```typescript
export const auth = pgSchema("auth")      // Better-Auth tables
export const product = pgSchema("product") // Application tables
```

**Interviews** (interviews.ts:12):
```typescript
product.interviews {
  id: uuid,
  role: text,
  level: text,
  status: text,  // "in_progress" | "completed"
  videoUrl: text,
  durationSeconds: integer,
  createdAt: timestamp,
  completedAt: timestamp
}
```

**Canvas** (canvas.ts:10):
```typescript
product.canvas_state {
  id: uuid,
  interviewId: uuid (UNIQUE, FK → interviews.id),
  elements: jsonb,  // [{ type: "excalidraw", elements }, { type: "code", code, language }]
  appState: jsonb,
  createdAt: timestamp
}
```

**Payments** (payments.ts:15):
```typescript
product.user_payment_methods {
  id: uuid,
  userId: text (UNIQUE),
  stripeCustomerId: text,
  defaultPaymentMethodId: text,
  cardLast4, cardBrand, cardExpMonth, cardExpYear
}

product.ap2_transactions {
  id: uuid,
  userId: text,
  interviewId: uuid,
  amountCents: integer,
  stripeChargeId: text,
  cartMandate: jsonb,
  paymentMandate: jsonb,
  status: text  // "completed" | "failed" | "refunded"
}
```

## API Routes

**Auth**: `/api/[...all]/route.ts:8`
```typescript
import { toNextJsHandler } from "better-auth/next-js"
export const { POST, GET } = toNextJsHandler(auth)
// Handles: /api/auth/sign-in, /api/auth/sign-up, /api/auth/session, etc.
```

**Recording Upload**: `/api/interviews/[id]/upload-recording/route.ts:15`
```typescript
POST /api/interviews/[id]/upload-recording
1. Validate interview ID (UUID)
2. Check interview exists
3. Upload to Vercel Blob: put(`recordings/${id}.webm`, file)
4. Update interview: { videoUrl, status: "completed", completedAt }
5. Return { url, interviewId }
```

**Payment Token**: `/api/payments/get-token/route.ts:12`
```typescript
POST /api/payments/get-token
Body: { user_id }
1. Fetch user_payment_methods from DB
2. Return encrypted token: { payment_method_id, stripe_customer_id, issued_at }
```

**Payment Execute**: `/api/payments/execute/route.ts:18`
```typescript
POST /api/payments/execute
Body: { payment_mandate: PaymentMandate }
1. Extract payment details
2. Verify cart hash
3. Create Stripe PaymentIntent
4. Confirm charge (off_session: true)
5. Store in ap2_transactions
6. Return payment receipt
```

## WebSocket Message Flow

**Client → Server**:
```typescript
// Audio chunk (16kHz PCM)
{ mime_type: "audio/pcm", data: "base64..." }

// Canvas screenshot
{ mime_type: "image/png", data: "base64..." }

// Payment confirmation
{ mime_type: "confirmation_response", data: { confirmation_id, approved } }
```

**Server → Client**:
```typescript
{
  author: "agent",
  is_partial: false,
  turn_complete: true,
  interrupted: false,
  parts: [
    { type: "audio/pcm", data: "base64..." },
    { type: "text", data: "..." }
  ],
  state: {
    interview_phase: "intro",
    pending_confirmation: {...},  // Payment UI trigger
    routing_decision: {...},
    candidate_info: {...}
  }
}
```

## Audio Pipeline

**Recording Flow**:
```
Microphone
  → getUserMedia({ audio: { sampleRate: 16000 } })
  → AudioWorkletRecorder (VAD + PCM conversion)
  → onAudioData(base64) → sendMessage({ mime_type: "audio/pcm", data })
  → WebSocket → Backend
```

**Playback Flow**:
```
Backend → WebSocket
  → onMessage({ parts: [{ type: "audio/pcm", data }] })
  → playAudio(base64)
  → AudioWorkletPlayer (queue buffering)
  → Speakers (24kHz)
```

**Barge-in Flow**:
```
User speaks → VAD detects (energy > 0.05, duration > 0.5s)
  → onSpeechStart()
  → flush() → Clear playback queue
  → Agent stops speaking
```

## Recording Pipeline

**Setup** (unified-interview.tsx):
```typescript
1. canvasStream = useCanvasStream(excalidrawAPI)  // 30 FPS
2. webcamStream = getUserMedia({ video: true })
3. compositeStream = useCompositeVideo({ canvasStream, webcamStream })
4. mixedAudioStream = useAudioMixer(micStream, agentStream)
5. startRecording(mixedAudioStream, compositeStream)
```

**Composite Layout** (use-composite-video.ts:45):
- Create 1920x1080 canvas
- Draw canvas video (full frame)
- Draw webcam (320x240, bottom-right, 20px padding, 2px white border)
- Capture composite at 30 FPS

**Upload** (on interview end):
```typescript
const blob = await stopRecording()  // Get WebM blob
await uploadRecording(interviewId, blob)
  → POST /api/interviews/[id]/upload-recording
  → Vercel Blob: put(`recordings/${id}.webm`, blob)
  → Update DB: { videoUrl, status: "completed" }
```

## Payment Flow (AP2)

**Display Payment UI**:
```typescript
// Orchestrator sets pending_confirmation in state
onStateUpdate(state) {
  if (state.pending_confirmation) {
    showConfirmationDialog({
      company: state.pending_confirmation.company,
      price: state.pending_confirmation.price
    })
  }
}
```

**User Confirms**:
```typescript
const handleConfirm = () => {
  sendMessage({
    mime_type: "confirmation_response",
    data: {
      confirmation_id: state.pending_confirmation.id,
      approved: true
    }
  })
}
```

**Backend Flow** (orchestrator handles):
1. Get payment token: `POST /api/payments/get-token`
2. Create payment mandate
3. Execute payment: Remote agent calls `POST /api/payments/execute`
4. Store receipt in state

## Common Tasks

### Add new WebSocket message type
1. Update `use-websocket.ts:45` - Add handler in `handleMessage()`
2. Define message structure in types
3. Send via: `sendMessage({ mime_type: "new_type", data })`

### Add new canvas type
1. Create component in `modules/interview/{type}/ui/components/`
2. Add tab in `unified-interview.tsx:45`
3. Update canvas state schema in `db/schema/canvas.ts`
4. Add persistence logic in save/restore handlers

### Modify audio processing
1. **Recorder**: Edit `public/audio-recorder-worklet.js:10`
   - VAD threshold: Line 45 (`ENERGY_THRESHOLD`)
   - Speech duration: Line 46 (`MIN_SPEECH_DURATION`)
2. **Player**: Edit `public/audio-player-worklet.js:10`
   - Buffer size: Line 30
   - Sample rate: Constructor parameter

### Add new API route
1. Create file in `app/api/{route}/route.ts`
2. Export HTTP methods: `export async function POST/GET/...`
3. Use Drizzle for DB queries: `import { db } from "@/db"`

## Debugging

**WebSocket**: Check `use-websocket.ts:45` - Add console.log in `handleMessage()`
**Audio**: Monitor worklet messages in DevTools Console
**Recording**: Check composite canvas rendering: `use-composite-video.ts:45`
**Database**: Use Drizzle Studio: `npm run db:studio`

## Development Tools

**Database Schema Management**:
```bash
npm run db:generate  # Generate SQL migrations from schema
npm run db:push      # Push schema to database (or: npm run db)
npm run db:studio    # Visual DB explorer (Drizzle Studio)
```

**Type Generation**:
```bash
npm run dev  # Auto-generates route types
```

**Testing**:
- Audio: Test with different sample rates (16kHz, 24kHz)
- WebSocket: Use DevTools Network tab (WS filter)
- Recording: Check composite canvas in Elements tab
