# Interview Agent - Implementation Roadmap

> **Project Overview**: AI-powered interview platform using Google ADK for multi-agent orchestration, supporting system design and coding interviews with real-time audio/video, canvas collaboration, and A2A remote agent evaluation.

**Current Stack**: Next.js 16 + React 19 + TypeScript (frontend) | Python 3.10 + Google ADK 1.16.0 (orchestrator) | PostgreSQL + Drizzle ORM | Better-Auth | Gemini 2.5 Flash Native Audio

---

## 1. Record Audio/Video and Store in Vercel Blob Store/S3

**Priority**: HIGH | **Complexity**: MEDIUM

### Current State
- ✅ **Audio streaming** working via WebSocket (PCM 16kHz format)
- ✅ **Audio worklets** implemented (`audio-recorder-worklet.js`, `audio-player-worklet.js`)
- ✅ **Video capture** working via `use-webcam.ts` (display only)
- ❌ **No persistence** - audio/video only streamed, not recorded
- ❌ **No storage integration**

### Implementation Design

#### Frontend Changes
**Location**: `/services/frontend/modules/interview/`

1. **Add MediaRecorder Integration**
   ```typescript
   // hooks/use-media-recorder.ts
   export function useMediaRecorder() {
     const [chunks, setChunks] = useState<Blob[]>([]);
     const [mediaRecorder, setMediaRecorder] = useState<MediaRecorder | null>(null);

     const startRecording = async (stream: MediaStream, mimeType: string) => {
       const recorder = new MediaRecorder(stream, { mimeType });
       recorder.ondataavailable = (e) => setChunks((prev) => [...prev, e.data]);
       recorder.start(1000); // Capture every 1s
       setMediaRecorder(recorder);
     };

     const stopRecording = async () => {
       return new Blob(chunks, { type: mimeType });
     };

     return { startRecording, stopRecording };
   }
   ```

2. **Update Interview Components**
   - Modify `system-design/index.tsx` to start recording on interview start
   - Modify `coding/index.tsx` similarly
   - Add recording status indicator to UI

#### Backend Changes
**Location**: `/services/frontend/app/api/`

1. **Create Storage Service**
   ```typescript
   // lib/storage/blob-storage.ts
   import { put } from '@vercel/blob';
   // OR
   import { S3Client, PutObjectCommand } from '@aws-sdk/client-s3';

   export async function uploadAudio(
     interviewId: string,
     blob: Blob
   ): Promise<string> {
     const filename = `audio/${interviewId}.webm`;

     // Option 1: Vercel Blob Store
     const { url } = await put(filename, blob, {
       access: 'public',
       addRandomSuffix: false,
     });

     // Option 2: AWS S3
     // const command = new PutObjectCommand({
     //   Bucket: process.env.S3_BUCKET,
     //   Key: filename,
     //   Body: Buffer.from(await blob.arrayBuffer()),
     // });
     // await s3Client.send(command);

     return url;
   }
   ```

2. **Create Upload API Routes**
   ```typescript
   // app/api/interviews/[id]/upload-media/route.ts
   export async function POST(req: Request, { params }: { params: { id: string } }) {
     const formData = await req.formData();
     const audioBlob = formData.get('audio') as File;
     const videoBlob = formData.get('video') as File;

     const [audioUrl, videoUrl] = await Promise.all([
       audioBlob ? uploadAudio(params.id, audioBlob) : null,
       videoBlob ? uploadVideo(params.id, videoBlob) : null,
     ]);

     // Update database
     await db.update(interviews)
       .set({ audioUrl, videoUrl, completedAt: new Date() })
       .where(eq(interviews.id, params.id));

     return NextResponse.json({ audioUrl, videoUrl });
   }
   ```

#### Database Schema Updates
**Location**: `/services/frontend/db/schema/interviews.ts`

```typescript
export const interviews = pgTable('interviews', {
  id: uuid('id').primaryKey().defaultRandom(),
  userId: text('user_id').notNull().references(() => user.id),
  role: text('role').notNull(),
  level: text('level').notNull(),
  status: text('status').notNull().default('in_progress'),
  audioUrl: text('audio_url'),           // NEW
  videoUrl: text('video_url'),           // NEW
  durationSeconds: integer('duration_seconds'), // NEW
  createdAt: timestamp('created_at').defaultNow(),
  completedAt: timestamp('completed_at'),
});
```

#### Environment Variables
```bash
# Option 1: Vercel Blob
BLOB_READ_WRITE_TOKEN=vercel_blob_xxx

# Option 2: AWS S3
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
AWS_REGION=us-east-1
S3_BUCKET=interview-agent-recordings
```

#### Testing Checklist
- [ ] Audio recording starts/stops correctly
- [ ] Video recording starts/stops correctly
- [ ] Uploads succeed to Blob/S3
- [ ] Database updates with URLs
- [ ] Playback works from stored URLs
- [ ] Handle network failures gracefully
- [ ] Test large file uploads (>100MB)

---

## 2. Store Audio Transcriptions and Canvas Details into DB

**Priority**: HIGH | **Complexity**: MEDIUM

### Current State
- ✅ **Real-time transcriptions** working (Gemini API provides input/output transcripts)
- ✅ **Canvas screenshots** captured every 10s via `use-canvas-screenshot.ts`
- ❌ **No transcription persistence** - only displayed in real-time
- ❌ **No canvas storage** - screenshots captured but not saved

### Implementation Design

#### Database Schema Extensions
**Location**: `/services/frontend/db/schema/`

1. **Create Transcriptions Table**
   ```typescript
   // transcriptions.ts
   export const transcriptions = pgTable('transcriptions', {
     id: uuid('id').primaryKey().defaultRandom(),
     interviewId: uuid('interview_id').notNull().references(() => interviews.id, { onDelete: 'cascade' }),
     speaker: text('speaker').notNull(), // 'candidate' | 'agent'
     text: text('text').notNull(),
     isFinal: boolean('is_final').notNull().default(false),
     timestamp: timestamp('timestamp').defaultNow(),
     sequenceNumber: integer('sequence_number'), // For ordering
   });

   export const transcriptionsIndex = index('transcriptions_interview_idx')
     .on(transcriptions.interviewId, transcriptions.timestamp);
   ```

2. **Create Canvas Snapshots Table**
   ```typescript
   // canvas-snapshots.ts
   export const canvasSnapshots = pgTable('canvas_snapshots', {
     id: uuid('id').primaryKey().defaultRandom(),
     interviewId: uuid('interview_id').notNull().references(() => interviews.id, { onDelete: 'cascade' }),
     snapshotUrl: text('snapshot_url').notNull(),
     timestamp: timestamp('timestamp').defaultNow(),
     elements: jsonb('elements'), // Excalidraw elements JSON
     appState: jsonb('app_state'), // Excalidraw app state JSON
   });

   export const canvasSnapshotsIndex = index('canvas_snapshots_interview_idx')
     .on(canvasSnapshots.interviewId, canvasSnapshots.timestamp);
   ```

3. **Update Interviews Table**
   ```typescript
   // interviews.ts
   export const interviews = pgTable('interviews', {
     // ... existing fields
     transcriptUrl: text('transcript_url'), // Link to full transcript export (JSON/TXT)
     canvasSnapshotCount: integer('canvas_snapshot_count').default(0),
   });
   ```

#### Backend API Routes
**Location**: `/services/frontend/app/api/`

1. **Transcription Storage API**
   ```typescript
   // app/api/interviews/[id]/transcriptions/route.ts
   export async function POST(req: Request, { params }: { params: { id: string } }) {
     const { speaker, text, isFinal, sequenceNumber } = await req.json();

     const transcription = await db.insert(transcriptions).values({
       interviewId: params.id,
       speaker,
       text,
       isFinal,
       sequenceNumber,
     }).returning();

     return NextResponse.json(transcription);
   }

   export async function GET(req: Request, { params }: { params: { id: string } }) {
     const transcript = await db.select()
       .from(transcriptions)
       .where(eq(transcriptions.interviewId, params.id))
       .orderBy(transcriptions.timestamp);

     return NextResponse.json(transcript);
   }
   ```

2. **Canvas Snapshot Storage API**
   ```typescript
   // app/api/interviews/[id]/canvas-snapshots/route.ts
   export async function POST(req: Request, { params }: { params: { id: string } }) {
     const formData = await req.formData();
     const screenshot = formData.get('screenshot') as File;
     const elements = formData.get('elements') as string;
     const appState = formData.get('appState') as string;

     // Upload screenshot to Blob/S3
     const snapshotUrl = await uploadCanvasSnapshot(params.id, screenshot);

     // Store metadata in DB
     const snapshot = await db.insert(canvasSnapshots).values({
       interviewId: params.id,
       snapshotUrl,
       elements: JSON.parse(elements),
       appState: JSON.parse(appState),
     }).returning();

     // Update count
     await db.update(interviews)
       .set({ canvasSnapshotCount: sql`${interviews.canvasSnapshotCount} + 1` })
       .where(eq(interviews.id, params.id));

     return NextResponse.json(snapshot);
   }
   ```

#### Frontend Integration
**Location**: `/services/frontend/modules/interview/`

1. **Update WebSocket Message Handler**
   ```typescript
   // hooks/use-interview-websocket.ts
   useEffect(() => {
     socket.on('message', async (msg: AgentResponse) => {
       // Store input transcription (candidate)
       if (msg.input_transcription?.is_final) {
         await fetch(`/api/interviews/${interviewId}/transcriptions`, {
           method: 'POST',
           body: JSON.stringify({
             speaker: 'candidate',
             text: msg.input_transcription.text,
             isFinal: true,
             sequenceNumber: transcriptCounter++,
           }),
         });
       }

       // Store output transcription (agent)
       if (msg.output_transcription?.is_final) {
         await fetch(`/api/interviews/${interviewId}/transcriptions`, {
           method: 'POST',
           body: JSON.stringify({
             speaker: 'agent',
             text: msg.output_transcription.text,
             isFinal: true,
             sequenceNumber: transcriptCounter++,
           }),
         });
       }
     });
   }, [socket]);
   ```

2. **Update Canvas Screenshot Hook**
   ```typescript
   // hooks/use-canvas-screenshot.ts
   const captureAndUpload = useCallback(async () => {
     const screenshot = await captureScreenshot();

     const formData = new FormData();
     formData.append('screenshot', screenshot.blob, `${screenshot.timestamp}.png`);
     formData.append('elements', JSON.stringify(excalidrawAPI?.getSceneElements()));
     formData.append('appState', JSON.stringify(excalidrawAPI?.getAppState()));

     await fetch(`/api/interviews/${interviewId}/canvas-snapshots`, {
       method: 'POST',
       body: formData,
     });
   }, [captureScreenshot, interviewId]);

   // Auto-upload every 10s
   useEffect(() => {
     const interval = setInterval(captureAndUpload, intervalMs);
     return () => clearInterval(interval);
   }, [captureAndUpload, intervalMs]);
   ```

#### Transcript Export Functionality
```typescript
// lib/transcript-exporter.ts
export async function exportTranscript(interviewId: string) {
  const transcript = await db.select()
    .from(transcriptions)
    .where(eq(transcriptions.interviewId, interviewId))
    .orderBy(transcriptions.timestamp);

  // Generate formatted transcript
  const formatted = transcript.map(t =>
    `[${t.timestamp}] ${t.speaker.toUpperCase()}: ${t.text}`
  ).join('\n');

  // Upload to storage
  const blob = new Blob([formatted], { type: 'text/plain' });
  const url = await uploadTranscript(interviewId, blob);

  // Update interview record
  await db.update(interviews)
    .set({ transcriptUrl: url })
    .where(eq(interviews.id, interviewId));

  return url;
}
```

#### Testing Checklist
- [ ] Transcriptions saved in real-time
- [ ] Canvas snapshots uploaded every 10s
- [ ] Transcript export generates correctly
- [ ] Database queries performant (indexed)
- [ ] Handle concurrent writes gracefully
- [ ] Replay functionality works from stored data

---

## 3. Update Interview Record with Status and Details

**Priority**: HIGH | **Complexity**: LOW

### Current State
- ✅ **Basic interview table** exists (`id`, `role`, `level`, `status`, `createdAt`, `completedAt`)
- ❌ **No user relationship** - missing `userId` foreign key
- ❌ **Limited metadata** - no question tracking, phase tracking, scores
- ❌ **No status workflow** - only `in_progress` status defined

### Implementation Design

#### Database Schema Enhancements
**Location**: `/services/frontend/db/schema/interviews.ts`

```typescript
export const interviewStatus = pgEnum('interview_status', [
  'scheduled',
  'in_progress',
  'completed',
  'abandoned',
  'failed',
]);

export const interviewType = pgEnum('interview_type', [
  'system_design',
  'coding',
  'behavioral', // Future
]);

export const interviews = pgTable('interviews', {
  // Identification
  id: uuid('id').primaryKey().defaultRandom(),
  userId: text('user_id').notNull().references(() => user.id, { onDelete: 'cascade' }),

  // Interview Details
  type: interviewType('type').notNull(),
  role: text('role').notNull(),
  level: text('level').notNull(),
  company: text('company'), // e.g., 'Google', 'Meta', 'Free Practice'
  questionId: uuid('question_id'), // FK to questions table (future)
  questionText: text('question_text'), // Store actual question asked

  // Status & Lifecycle
  status: interviewStatus('status').notNull().default('in_progress'),
  currentPhase: text('current_phase'), // 'routing', 'intro', 'interview', 'closing', 'done'

  // Media & Artifacts
  audioUrl: text('audio_url'),
  videoUrl: text('video_url'),
  transcriptUrl: text('transcript_url'),
  canvasSnapshotCount: integer('canvas_snapshot_count').default(0),

  // Metrics
  durationSeconds: integer('duration_seconds'),
  score: decimal('score', { precision: 4, scale: 2 }), // e.g., 8.50

  // Metadata
  sessionState: jsonb('session_state'), // Store ADK session state snapshot
  metadata: jsonb('metadata'), // Flexible field for additional data

  // Timestamps
  createdAt: timestamp('created_at').defaultNow(),
  startedAt: timestamp('started_at'),
  completedAt: timestamp('completed_at'),

  // Soft Delete
  deletedAt: timestamp('deleted_at'),
});

// Indexes
export const interviewsUserIndex = index('interviews_user_idx').on(interviews.userId);
export const interviewsStatusIndex = index('interviews_status_idx').on(interviews.status);
export const interviewsCreatedIndex = index('interviews_created_idx').on(interviews.createdAt);
```

#### Status Workflow State Machine
```typescript
// lib/interview-state-machine.ts
export type InterviewStatus = 'scheduled' | 'in_progress' | 'completed' | 'abandoned' | 'failed';
export type InterviewPhase = 'routing' | 'intro' | 'interview' | 'closing' | 'done';

export const STATUS_TRANSITIONS: Record<InterviewStatus, InterviewStatus[]> = {
  scheduled: ['in_progress', 'abandoned'],
  in_progress: ['completed', 'abandoned', 'failed'],
  completed: [],
  abandoned: [],
  failed: [],
};

export function canTransition(from: InterviewStatus, to: InterviewStatus): boolean {
  return STATUS_TRANSITIONS[from]?.includes(to) ?? false;
}

export async function updateInterviewStatus(
  interviewId: string,
  newStatus: InterviewStatus,
  updates: Partial<typeof interviews.$inferInsert> = {}
) {
  const interview = await db.select().from(interviews).where(eq(interviews.id, interviewId)).limit(1);

  if (!interview[0]) {
    throw new Error('Interview not found');
  }

  if (!canTransition(interview[0].status as InterviewStatus, newStatus)) {
    throw new Error(`Cannot transition from ${interview[0].status} to ${newStatus}`);
  }

  const now = new Date();
  const statusUpdates: Record<string, any> = { status: newStatus };

  if (newStatus === 'in_progress' && !interview[0].startedAt) {
    statusUpdates.startedAt = now;
  }

  if (newStatus === 'completed') {
    statusUpdates.completedAt = now;
    statusUpdates.durationSeconds = interview[0].startedAt
      ? Math.floor((now.getTime() - interview[0].startedAt.getTime()) / 1000)
      : null;
  }

  return db.update(interviews)
    .set({ ...statusUpdates, ...updates })
    .where(eq(interviews.id, interviewId))
    .returning();
}
```

#### API Routes for Status Management
**Location**: `/services/frontend/app/api/interviews/`

```typescript
// [id]/status/route.ts
export async function PATCH(req: Request, { params }: { params: { id: string } }) {
  const { status, phase, metadata } = await req.json();

  const updates: Partial<typeof interviews.$inferInsert> = {};

  if (phase) {
    updates.currentPhase = phase;
  }

  if (metadata) {
    updates.metadata = metadata;
  }

  const updated = await updateInterviewStatus(params.id, status, updates);

  return NextResponse.json(updated);
}

// [id]/route.ts
export async function GET(req: Request, { params }: { params: { id: string } }) {
  const interview = await db.select()
    .from(interviews)
    .leftJoin(user, eq(interviews.userId, user.id))
    .where(eq(interviews.id, params.id))
    .limit(1);

  if (!interview[0]) {
    return NextResponse.json({ error: 'Not found' }, { status: 404 });
  }

  // Fetch related data
  const [transcriptCount, snapshotCount] = await Promise.all([
    db.select({ count: sql`count(*)` })
      .from(transcriptions)
      .where(eq(transcriptions.interviewId, params.id)),
    db.select({ count: sql`count(*)` })
      .from(canvasSnapshots)
      .where(eq(canvasSnapshots.interviewId, params.id)),
  ]);

  return NextResponse.json({
    ...interview[0],
    stats: {
      transcriptCount: transcriptCount[0].count,
      snapshotCount: snapshotCount[0].count,
    },
  });
}
```

#### Orchestrator Integration
**Location**: `/services/interview-orchestrator/interview_orchestrator/`

Update WebSocket handler to sync status with database:

```python
# websocket_handler.py
async def handle_session_event(user_id: str, event: dict):
    phase = event.get("interview_phase")

    # Update database via API
    async with httpx.AsyncClient() as client:
        await client.patch(
            f"{FRONTEND_API_URL}/api/interviews/{session.interview_id}/status",
            json={
                "phase": phase,
                "metadata": {
                    "interview_type": session.state.get("interview_type"),
                    "company": session.state.get("routing_decision", {}).get("company"),
                },
            },
        )

    # Update session state
    if phase == "done":
        await client.patch(
            f"{FRONTEND_API_URL}/api/interviews/{session.interview_id}/status",
            json={"status": "completed"},
        )
```

#### Testing Checklist
- [ ] Status transitions enforced correctly
- [ ] Timestamps auto-populate (startedAt, completedAt)
- [ ] Duration calculated correctly
- [ ] Phase updates sync from orchestrator
- [ ] User-interview relationship enforced
- [ ] Metadata stored and retrieved correctly
- [ ] Soft delete works (deletedAt)

---

## 4. Get Feedback from Agent on Interview and Update UX to Present Details

**Priority**: MEDIUM | **Complexity**: HIGH

### Current State
- ✅ **Remote agents** (Google, Meta) provide specialized evaluation during interview
- ✅ **Mock feedback** displayed in home view (score: 8.5, strengths, improvements)
- ❌ **No feedback storage** - no database schema
- ❌ **No automated evaluation** - no LLM-based post-interview analysis
- ❌ **No rubric system** - no structured scoring criteria

### Implementation Design

#### Database Schema for Feedback
**Location**: `/services/frontend/db/schema/`

```typescript
// feedback.ts
export const feedbackCategory = pgEnum('feedback_category', [
  'technical_depth',
  'system_design_skills',
  'problem_solving',
  'communication',
  'clarification',
  'trade_offs',
  'scalability',
  'code_quality', // For coding interviews
]);

export const feedback = pgTable('feedback', {
  id: uuid('id').primaryKey().defaultRandom(),
  interviewId: uuid('interview_id').notNull().references(() => interviews.id, { onDelete: 'cascade' }),

  // Overall Assessment
  overallScore: decimal('overall_score', { precision: 4, scale: 2 }).notNull(), // 0-10
  summary: text('summary'), // Brief summary paragraph

  // Strengths & Improvements
  strengths: text('strengths').array(), // Array of strength points
  improvements: text('improvements').array(), // Array of improvement areas

  // Category Scores
  categoryScores: jsonb('category_scores'), // { technical_depth: 8, communication: 7, ... }

  // Detailed Feedback
  detailedFeedback: text('detailed_feedback'), // Long-form evaluation

  // Rubric-based Assessment
  rubricScores: jsonb('rubric_scores'), // { requirement_gathering: 4/5, api_design: 3/5, ... }

  // AI Metadata
  generatedBy: text('generated_by').notNull(), // 'gpt-4', 'gemini-2.5-pro', 'google_agent', etc.
  promptVersion: text('prompt_version'), // Track which prompt generated this

  createdAt: timestamp('created_at').defaultNow(),
});

export const feedbackIndex = index('feedback_interview_idx').on(feedback.interviewId);
```

#### Evaluation Service
**Location**: `/services/frontend/lib/evaluation/`

```typescript
// evaluator.ts
import { GoogleGenerativeAI } from '@google/generative-ai';

export interface EvaluationInput {
  interviewId: string;
  transcript: string;
  canvasSnapshots: string[]; // URLs to screenshots
  questionText: string;
  interviewType: 'system_design' | 'coding';
  level: 'junior' | 'mid' | 'senior' | 'staff' | 'principal';
}

export interface EvaluationResult {
  overallScore: number;
  summary: string;
  strengths: string[];
  improvements: string[];
  categoryScores: Record<string, number>;
  rubricScores: Record<string, number>;
  detailedFeedback: string;
}

const SYSTEM_DESIGN_RUBRIC = {
  requirement_gathering: {
    weight: 0.15,
    criteria: [
      'Asked clarifying questions',
      'Identified functional requirements',
      'Identified non-functional requirements (scale, latency, consistency)',
    ],
  },
  high_level_design: {
    weight: 0.25,
    criteria: [
      'Identified major components',
      'Drew clear architecture diagram',
      'Explained data flow',
    ],
  },
  deep_dive: {
    weight: 0.25,
    criteria: [
      'Detailed component design',
      'Database schema design',
      'API design',
    ],
  },
  scalability: {
    weight: 0.20,
    criteria: [
      'Discussed bottlenecks',
      'Proposed scaling strategies (sharding, caching, CDN)',
      'Load balancing and replication',
    ],
  },
  communication: {
    weight: 0.15,
    criteria: [
      'Clear explanations',
      'Structured approach',
      'Handled feedback well',
    ],
  },
};

export async function evaluateInterview(input: EvaluationInput): Promise<EvaluationResult> {
  const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY!);
  const model = genAI.getGenerativeModel({ model: 'gemini-2.5-pro' });

  // Prepare evaluation prompt
  const prompt = `
You are an expert technical interviewer evaluating a ${input.interviewType} interview for a ${input.level} level candidate.

**Question Asked:**
${input.questionText}

**Full Transcript:**
${input.transcript}

**Canvas Diagrams:**
${input.canvasSnapshots.length} diagrams were created during the interview (images attached).

**Evaluation Rubric for System Design:**
${JSON.stringify(SYSTEM_DESIGN_RUBRIC, null, 2)}

**Instructions:**
1. Evaluate the candidate based on the rubric above
2. Assign scores (0-5) for each rubric category
3. Calculate weighted overall score (0-10)
4. Identify 3-5 key strengths
5. Identify 3-5 areas for improvement
6. Provide detailed feedback (2-3 paragraphs)
7. Provide a brief summary (1-2 sentences)

**Response Format (JSON):**
{
  "overallScore": 7.5,
  "rubricScores": {
    "requirement_gathering": 4,
    "high_level_design": 3,
    ...
  },
  "categoryScores": {
    "technical_depth": 7,
    "communication": 8,
    ...
  },
  "strengths": ["...", "..."],
  "improvements": ["...", "..."],
  "summary": "...",
  "detailedFeedback": "..."
}
`;

  // Attach canvas screenshots
  const imageParts = await Promise.all(
    input.canvasSnapshots.map(async (url) => {
      const response = await fetch(url);
      const buffer = await response.arrayBuffer();
      return {
        inlineData: {
          data: Buffer.from(buffer).toString('base64'),
          mimeType: 'image/png',
        },
      };
    })
  );

  const result = await model.generateContent([prompt, ...imageParts]);
  const responseText = result.response.text();

  // Parse JSON response
  const jsonMatch = responseText.match(/\{[\s\S]*\}/);
  if (!jsonMatch) {
    throw new Error('Failed to parse evaluation response');
  }

  return JSON.parse(jsonMatch[0]);
}
```

#### API Route for Generating Feedback
**Location**: `/services/frontend/app/api/interviews/[id]/feedback/`

```typescript
// route.ts
export async function POST(req: Request, { params }: { params: { id: string } }) {
  const interviewId = params.id;

  // Fetch interview data
  const [interview] = await db.select()
    .from(interviews)
    .where(eq(interviews.id, interviewId))
    .limit(1);

  if (!interview) {
    return NextResponse.json({ error: 'Interview not found' }, { status: 404 });
  }

  // Fetch transcript
  const transcriptRows = await db.select()
    .from(transcriptions)
    .where(eq(transcriptions.interviewId, interviewId))
    .orderBy(transcriptions.timestamp);

  const transcript = transcriptRows
    .map(t => `[${t.speaker}]: ${t.text}`)
    .join('\n');

  // Fetch canvas snapshots
  const snapshots = await db.select()
    .from(canvasSnapshots)
    .where(eq(canvasSnapshots.interviewId, interviewId))
    .orderBy(canvasSnapshots.timestamp);

  const snapshotUrls = snapshots.map(s => s.snapshotUrl);

  // Run evaluation
  const evaluation = await evaluateInterview({
    interviewId,
    transcript,
    canvasSnapshots: snapshotUrls,
    questionText: interview.questionText || '',
    interviewType: interview.type as 'system_design' | 'coding',
    level: interview.level as any,
  });

  // Store feedback
  const [feedbackRecord] = await db.insert(feedback).values({
    interviewId,
    overallScore: evaluation.overallScore.toString(),
    summary: evaluation.summary,
    strengths: evaluation.strengths,
    improvements: evaluation.improvements,
    categoryScores: evaluation.categoryScores,
    rubricScores: evaluation.rubricScores,
    detailedFeedback: evaluation.detailedFeedback,
    generatedBy: 'gemini-2.5-pro',
    promptVersion: 'v1.0',
  }).returning();

  // Update interview with overall score
  await db.update(interviews)
    .set({ score: evaluation.overallScore.toString() })
    .where(eq(interviews.id, interviewId));

  return NextResponse.json(feedbackRecord);
}

export async function GET(req: Request, { params }: { params: { id: string } }) {
  const feedbackRecord = await db.select()
    .from(feedback)
    .where(eq(feedback.interviewId, params.id))
    .limit(1);

  if (!feedbackRecord[0]) {
    return NextResponse.json({ error: 'Feedback not found' }, { status: 404 });
  }

  return NextResponse.json(feedbackRecord[0]);
}
```

#### UX Updates for Feedback Display
**Location**: `/services/frontend/modules/interviews/`

```typescript
// components/feedback-display.tsx
export function FeedbackDisplay({ interviewId }: { interviewId: string }) {
  const { data: feedback, isLoading } = useSWR(
    `/api/interviews/${interviewId}/feedback`,
    fetcher
  );

  if (isLoading) return <FeedbackSkeleton />;
  if (!feedback) return <GenerateFeedbackButton interviewId={interviewId} />;

  return (
    <div className="space-y-6">
      {/* Overall Score */}
      <Card>
        <CardHeader>
          <CardTitle>Overall Performance</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <div className="text-6xl font-bold">{feedback.overallScore}</div>
            <div className="text-sm text-muted-foreground">/ 10</div>
          </div>
          <p className="mt-4 text-muted-foreground">{feedback.summary}</p>
        </CardContent>
      </Card>

      {/* Category Breakdown */}
      <Card>
        <CardHeader>
          <CardTitle>Category Scores</CardTitle>
        </CardHeader>
        <CardContent>
          {Object.entries(feedback.categoryScores).map(([category, score]) => (
            <div key={category} className="mb-4">
              <div className="flex justify-between mb-2">
                <span className="capitalize">{category.replace('_', ' ')}</span>
                <span className="font-semibold">{score}/10</span>
              </div>
              <Progress value={(score as number) * 10} />
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Strengths & Improvements */}
      <div className="grid md:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CheckCircle className="text-green-500" />
              Strengths
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {feedback.strengths.map((strength, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="text-green-500">•</span>
                  <span>{strength}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <AlertCircle className="text-amber-500" />
              Areas for Improvement
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ul className="space-y-2">
              {feedback.improvements.map((improvement, i) => (
                <li key={i} className="flex items-start gap-2">
                  <span className="text-amber-500">•</span>
                  <span>{improvement}</span>
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      </div>

      {/* Detailed Feedback */}
      <Card>
        <CardHeader>
          <CardTitle>Detailed Feedback</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="whitespace-pre-wrap">{feedback.detailedFeedback}</p>
        </CardContent>
      </Card>

      {/* Rubric Scores */}
      <Card>
        <CardHeader>
          <CardTitle>Rubric Assessment</CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Criteria</TableHead>
                <TableHead className="text-right">Score</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {Object.entries(feedback.rubricScores).map(([criterion, score]) => (
                <TableRow key={criterion}>
                  <TableCell className="capitalize">{criterion.replace('_', ' ')}</TableCell>
                  <TableCell className="text-right font-semibold">{score}/5</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}
```

#### Testing Checklist
- [ ] Feedback generation works for completed interviews
- [ ] Rubric scores calculated correctly
- [ ] Canvas screenshots analyzed in evaluation
- [ ] Transcript parsed and analyzed
- [ ] UI displays all feedback components
- [ ] Strengths/improvements are actionable
- [ ] Overall score matches rubric weights
- [ ] Performance acceptable (<30s generation time)

---

## 5. Send Canvas Screenshots to Orchestrator and Use A2A to Pass to Remote Agents

**Priority**: MEDIUM | **Complexity**: MEDIUM

### Current State
- ✅ **A2A protocol** fully implemented for remote agents (Google, Meta)
- ✅ **Canvas screenshots** captured every 10s on frontend
- ❌ **Screenshots NOT sent to orchestrator** during interview
- ❌ **Remote agents DON'T receive visual context** - only text

### Implementation Design

#### Frontend → Orchestrator Communication
**Location**: `/services/frontend/modules/interview/hooks/`

```typescript
// use-canvas-screenshot.ts
export function useCanvasScreenshot({
  interviewId,
  intervalMs = 10000,
  sendToOrchestrator = true,
}: {
  interviewId: string;
  intervalMs?: number;
  sendToOrchestrator?: boolean;
}) {
  const { sendMessage } = useInterviewWebSocket();

  const captureAndSend = useCallback(async () => {
    const screenshot = await captureScreenshot();

    // Convert to base64
    const base64 = await blobToBase64(screenshot.blob);

    // Send to orchestrator via WebSocket
    if (sendToOrchestrator) {
      sendMessage({
        mime_type: 'image/png',
        data: base64,
      });
    }

    // Also save to storage for post-interview analysis
    await uploadCanvasSnapshot(interviewId, screenshot);
  }, [captureScreenshot, sendMessage, interviewId]);

  // Auto-capture every 10s
  useEffect(() => {
    const interval = setInterval(captureAndSend, intervalMs);
    return () => clearInterval(interval);
  }, [captureAndSend, intervalMs]);

  return { captureAndSend };
}
```

#### Orchestrator WebSocket Handler
**Location**: `/services/interview-orchestrator/interview_orchestrator/websocket_handler.py`

```python
async def handle_client_message(user_id: str, message: dict):
    mime_type = message.get("mime_type")
    data = message.get("data")

    if mime_type == "image/png":
        # Store screenshot in session state
        if "canvas_screenshots" not in session.state:
            session.state["canvas_screenshots"] = []

        session.state["canvas_screenshots"].append({
            "data": data,
            "timestamp": time.time(),
        })

        # Keep only last 5 screenshots to avoid memory bloat
        if len(session.state["canvas_screenshots"]) > 5:
            session.state["canvas_screenshots"].pop(0)

        logger.info(f"Received canvas screenshot for user {user_id}")

    elif mime_type in ["audio/pcm", "audio/webm"]:
        # Existing audio handling
        await session.add_content(...)
```

#### Update Design Agent to Send Screenshots to Remote Agents
**Location**: `/services/interview-orchestrator/interview_orchestrator/interview_types/system_design/`

```python
# design_agent.py
from google.adk.tools.remote_a2a_agent import RemoteA2aAgent
from google.adk.content import Part, InlineData

async def design_agent_instruction(ctx):
    company = ctx.session.state.get("routing_decision", {}).get("company")
    question = ctx.session.state.get("interview_question")
    screenshots = ctx.session.state.get("canvas_screenshots", [])

    # Get latest screenshot
    latest_screenshot = screenshots[-1] if screenshots else None

    instruction = f"""
You are conducting a {company} system design interview.

Question: {question}

The candidate is drawing their design on a canvas. You have access to their latest diagram.

**Your responsibilities:**
1. Ask clarifying questions about their design
2. Challenge their design decisions
3. Use remote agents to evaluate specific aspects:
   - Use google_agent for scalability analysis
   - Use meta_agent for social graph optimization

**Current diagram:**
{f"Screenshot captured at {latest_screenshot['timestamp']}" if latest_screenshot else "No diagram yet"}
"""

    return instruction

# Create design agent with vision capability
design_agent = LlmAgent(
    name="design_agent",
    model=Gemini(
        model="gemini-2.5-flash-vision",  # Use vision model
    ),
    instruction_func=design_agent_instruction,
    tools=[google_agent, meta_agent],
)

# Override tool execution to include screenshots
async def execute_remote_agent_with_screenshot(
    agent: RemoteA2aAgent,
    query: str,
    ctx
):
    screenshots = ctx.session.state.get("canvas_screenshots", [])

    if not screenshots:
        # No screenshot, just send text
        return await agent.execute(query)

    # Prepare multimodal request
    latest_screenshot = screenshots[-1]

    # A2A protocol supports multimodal content
    response = await agent.call_skill(
        skill_id="analyze_design",
        inputs={
            "query": query,
            "diagram": {
                "mime_type": "image/png",
                "data": latest_screenshot["data"],
            }
        }
    )

    return response
```

#### Update Remote Agents to Accept Screenshots
**Location**: `/services/google-agent/` and `/services/meta-agent/`

```python
# google_agent/agent.py
from google.adk import FunctionTool
from google.adk.content import Part, InlineData

@FunctionTool
async def analyze_scale_requirements(
    query: str,
    diagram: dict = None,
) -> str:
    """
    Analyze scale requirements for a system design.

    Args:
        query: Text description of requirements
        diagram: Optional diagram image (base64 PNG)
    """
    model = genai.GenerativeModel("gemini-2.5-pro-vision")

    # Prepare multimodal prompt
    parts = [
        f"Analyze the following system design for scale requirements:\n\n{query}",
    ]

    if diagram:
        parts.append(Part(
            inline_data=InlineData(
                mime_type="image/png",
                data=diagram["data"],
            )
        ))
        parts.append("\n\nBased on the diagram above, provide:")
    else:
        parts.append("\n\nProvide:")

    parts.append("""
1. Estimated QPS (queries per second)
2. Storage requirements
3. Bandwidth requirements
4. Bottlenecks in the current design
5. Scaling recommendations
""")

    response = await model.generate_content_async(parts)
    return response.text


# Update agent card to indicate vision support
AGENT_CARD = {
    "name": "Google System Design Expert",
    "skills": [
        {
            "id": "analyze_scale_requirements",
            "name": "Analyze Scale Requirements",
            "description": "Analyze system scale requirements with optional diagram",
            "inputModes": ["text", "image"],  # Supports images!
            "outputModes": ["text"],
        },
        # ... other skills
    ],
}
```

#### Update A2A Protocol for Multimodal Content
**Location**: `/services/interview-orchestrator/interview_orchestrator/shared/agent_registry.py`

```python
async def call_remote_agent_skill(
    agent: RemoteA2aAgent,
    skill_id: str,
    text_input: str,
    image_input: str = None,
) -> str:
    """
    Call a remote agent skill with multimodal input.
    """
    url = f"{agent.base_url}/skills/{skill_id}/execute"

    payload = {
        "inputs": {
            "text": text_input,
        }
    }

    if image_input:
        payload["inputs"]["image"] = {
            "mime_type": "image/png",
            "data": image_input,
        }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)
        response.raise_for_status()
        return response.json()["output"]
```

#### Testing Checklist
- [ ] Canvas screenshots sent to orchestrator every 10s
- [ ] Screenshots stored in session state
- [ ] Design agent includes screenshot in remote agent calls
- [ ] Google agent receives and analyzes diagrams
- [ ] Meta agent receives and analyzes diagrams
- [ ] Vision model correctly interprets diagrams
- [ ] Performance acceptable with image transfer
- [ ] Memory usage controlled (limit stored screenshots)

---

## 6. Integrate A2P (Agent-to-Person) for User Payments

**Priority**: LOW | **Complexity**: MEDIUM

### Current State
- ✅ **UI shows Premium badges** on Google/Meta company cards
- ✅ **Better-Auth** authentication system in place
- ❌ **No payment integration** (Stripe, LemonSqueezy, etc.)
- ❌ **No subscription management**
- ❌ **No feature gating** for premium companies

### Implementation Design

#### Payment Provider: Stripe

**Pricing Model:**
- **Free Tier**: Free Practice interviews (unlimited)
- **Premium Tier**: $29/month or $5/interview
  - Google, Meta, Amazon, Netflix companies
  - Advanced evaluation
  - Video recording
  - Detailed feedback reports

#### Database Schema
**Location**: `/services/frontend/db/schema/`

```typescript
// subscriptions.ts
export const subscriptionPlan = pgEnum('subscription_plan', [
  'free',
  'premium_monthly',
  'pay_per_interview',
]);

export const subscriptionStatus = pgEnum('subscription_status', [
  'active',
  'canceled',
  'expired',
  'trialing',
]);

export const subscriptions = pgTable('subscriptions', {
  id: uuid('id').primaryKey().defaultRandom(),
  userId: text('user_id').notNull().references(() => user.id, { onDelete: 'cascade' }),

  plan: subscriptionPlan('plan').notNull(),
  status: subscriptionStatus('status').notNull(),

  // Stripe IDs
  stripeCustomerId: text('stripe_customer_id'),
  stripeSubscriptionId: text('stripe_subscription_id'),
  stripePriceId: text('stripe_price_id'),

  // Billing
  currentPeriodStart: timestamp('current_period_start'),
  currentPeriodEnd: timestamp('current_period_end'),
  cancelAtPeriodEnd: boolean('cancel_at_period_end').default(false),

  // Credits (for pay-per-interview)
  creditsRemaining: integer('credits_remaining').default(0),

  createdAt: timestamp('created_at').defaultNow(),
  updatedAt: timestamp('updated_at').defaultNow(),
});

// payments.ts (for pay-per-interview)
export const payments = pgTable('payments', {
  id: uuid('id').primaryKey().defaultRandom(),
  userId: text('user_id').notNull().references(() => user.id),
  interviewId: uuid('interview_id').references(() => interviews.id),

  amount: integer('amount').notNull(), // in cents
  currency: text('currency').notNull().default('usd'),

  stripePaymentIntentId: text('stripe_payment_intent_id'),
  status: text('status').notNull(), // 'succeeded', 'pending', 'failed'

  createdAt: timestamp('created_at').defaultNow(),
});
```

#### Environment Variables
```bash
# Stripe
STRIPE_SECRET_KEY=sk_live_xxx
STRIPE_PUBLISHABLE_KEY=pk_live_xxx
STRIPE_WEBHOOK_SECRET=whsec_xxx

# Stripe Price IDs
STRIPE_PREMIUM_MONTHLY_PRICE_ID=price_xxx
STRIPE_SINGLE_INTERVIEW_PRICE_ID=price_xxx
```

#### Stripe Setup Script
```typescript
// scripts/setup-stripe.ts
import Stripe from 'stripe';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!);

async function setupProducts() {
  // Create Premium Monthly product
  const premiumProduct = await stripe.products.create({
    name: 'Premium Interview Access',
    description: 'Unlimited interviews with premium companies',
  });

  const premiumPrice = await stripe.prices.create({
    product: premiumProduct.id,
    unit_amount: 2900, // $29.00
    currency: 'usd',
    recurring: {
      interval: 'month',
    },
  });

  // Create Pay-Per-Interview product
  const singleProduct = await stripe.products.create({
    name: 'Single Premium Interview',
    description: 'One-time access to premium company interview',
  });

  const singlePrice = await stripe.prices.create({
    product: singleProduct.id,
    unit_amount: 500, // $5.00
    currency: 'usd',
  });

  console.log('Premium Monthly Price ID:', premiumPrice.id);
  console.log('Single Interview Price ID:', singlePrice.id);
}

setupProducts();
```

#### API Routes for Payments
**Location**: `/services/frontend/app/api/payments/`

```typescript
// create-checkout/route.ts
import Stripe from 'stripe';

const stripe = new Stripe(process.env.STRIPE_SECRET_KEY!);

export async function POST(req: Request) {
  const { priceId, userId, mode } = await req.json();

  // Get or create Stripe customer
  let subscription = await db.select()
    .from(subscriptions)
    .where(eq(subscriptions.userId, userId))
    .limit(1);

  let customerId = subscription[0]?.stripeCustomerId;

  if (!customerId) {
    const user = await db.select().from(users).where(eq(users.id, userId)).limit(1);
    const customer = await stripe.customers.create({
      email: user[0].email,
      metadata: { userId },
    });
    customerId = customer.id;
  }

  // Create checkout session
  const session = await stripe.checkout.sessions.create({
    customer: customerId,
    mode: mode, // 'subscription' or 'payment'
    line_items: [
      {
        price: priceId,
        quantity: 1,
      },
    ],
    success_url: `${process.env.NEXT_PUBLIC_APP_URL}/dashboard?payment=success`,
    cancel_url: `${process.env.NEXT_PUBLIC_APP_URL}/pricing?payment=canceled`,
    metadata: { userId },
  });

  return NextResponse.json({ url: session.url });
}

// webhook/route.ts
export async function POST(req: Request) {
  const body = await req.text();
  const sig = req.headers.get('stripe-signature')!;

  let event: Stripe.Event;

  try {
    event = stripe.webhooks.constructEvent(
      body,
      sig,
      process.env.STRIPE_WEBHOOK_SECRET!
    );
  } catch (err) {
    return NextResponse.json({ error: 'Webhook error' }, { status: 400 });
  }

  switch (event.type) {
    case 'checkout.session.completed':
      const session = event.data.object as Stripe.Checkout.Session;
      await handleCheckoutComplete(session);
      break;

    case 'customer.subscription.updated':
      const subscription = event.data.object as Stripe.Subscription;
      await handleSubscriptionUpdate(subscription);
      break;

    case 'customer.subscription.deleted':
      const deletedSub = event.data.object as Stripe.Subscription;
      await handleSubscriptionCanceled(deletedSub);
      break;

    case 'invoice.payment_succeeded':
      const invoice = event.data.object as Stripe.Invoice;
      await handlePaymentSucceeded(invoice);
      break;
  }

  return NextResponse.json({ received: true });
}

async function handleCheckoutComplete(session: Stripe.Checkout.Session) {
  const userId = session.metadata!.userId;

  if (session.mode === 'subscription') {
    // Create/update subscription record
    await db.insert(subscriptions).values({
      userId,
      plan: 'premium_monthly',
      status: 'active',
      stripeCustomerId: session.customer as string,
      stripeSubscriptionId: session.subscription as string,
      stripePriceId: session.line_items?.data[0]?.price?.id,
      currentPeriodStart: new Date(),
      currentPeriodEnd: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000),
    });
  } else {
    // Pay-per-interview: add credits
    await db.insert(subscriptions).values({
      userId,
      plan: 'pay_per_interview',
      status: 'active',
      creditsRemaining: 1,
    }).onConflictDoUpdate({
      target: subscriptions.userId,
      set: {
        creditsRemaining: sql`${subscriptions.creditsRemaining} + 1`,
      },
    });

    // Record payment
    await db.insert(payments).values({
      userId,
      amount: session.amount_total!,
      currency: session.currency!,
      stripePaymentIntentId: session.payment_intent as string,
      status: 'succeeded',
    });
  }
}
```

#### Feature Gating Middleware
**Location**: `/services/frontend/lib/access-control.ts`

```typescript
export async function checkInterviewAccess(
  userId: string,
  company: string
): Promise<{ allowed: boolean; reason?: string }> {
  // Free companies always allowed
  const FREE_COMPANIES = ['Free Practice'];
  if (FREE_COMPANIES.includes(company)) {
    return { allowed: true };
  }

  // Check subscription
  const subscription = await db.select()
    .from(subscriptions)
    .where(eq(subscriptions.userId, userId))
    .limit(1);

  if (!subscription[0]) {
    return { allowed: false, reason: 'No active subscription' };
  }

  const sub = subscription[0];

  // Premium monthly: unlimited access
  if (sub.plan === 'premium_monthly' && sub.status === 'active') {
    const now = new Date();
    if (sub.currentPeriodEnd && now < sub.currentPeriodEnd) {
      return { allowed: true };
    }
    return { allowed: false, reason: 'Subscription expired' };
  }

  // Pay-per-interview: check credits
  if (sub.plan === 'pay_per_interview') {
    if (sub.creditsRemaining && sub.creditsRemaining > 0) {
      // Deduct credit
      await db.update(subscriptions)
        .set({ creditsRemaining: sub.creditsRemaining - 1 })
        .where(eq(subscriptions.id, sub.id));

      return { allowed: true };
    }
    return { allowed: false, reason: 'No credits remaining' };
  }

  return { allowed: false, reason: 'Invalid subscription' };
}
```

#### UI Updates
**Location**: `/services/frontend/modules/home/`

```typescript
// components/company-card.tsx
export function CompanyCard({ company }: { company: Company }) {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);

  const isPremium = !['Free Practice'].includes(company.name);
  const { data: subscription } = useSWR('/api/subscriptions/current');

  const hasAccess = !isPremium || subscription?.status === 'active';

  const handleStart = async () => {
    if (!hasAccess) {
      // Redirect to pricing
      router.push('/pricing');
      return;
    }

    // Check access
    const response = await fetch('/api/interviews/check-access', {
      method: 'POST',
      body: JSON.stringify({ company: company.name }),
    });

    const { allowed, reason } = await response.json();

    if (!allowed) {
      toast.error(reason);
      router.push('/pricing');
      return;
    }

    // Start interview
    router.push(`/interview?company=${company.name}`);
  };

  return (
    <Card className={isPremium && !hasAccess ? 'opacity-75' : ''}>
      <CardHeader>
        {isPremium && (
          <Badge className="absolute top-4 right-4">Premium</Badge>
        )}
        <CardTitle>{company.name}</CardTitle>
      </CardHeader>
      <CardContent>
        <Button onClick={handleStart} disabled={loading}>
          {hasAccess ? 'Start Interview' : 'Upgrade to Access'}
        </Button>
      </CardContent>
    </Card>
  );
}

// pages/pricing.tsx
export default function PricingPage() {
  return (
    <div className="grid md:grid-cols-3 gap-6">
      {/* Free Tier */}
      <PricingCard
        title="Free"
        price="$0"
        features={[
          'Unlimited Free Practice interviews',
          'Basic feedback',
          'Audio only',
        ]}
        cta="Get Started"
        href="/dashboard"
      />

      {/* Premium Monthly */}
      <PricingCard
        title="Premium Monthly"
        price="$29"
        period="/month"
        features={[
          'Unlimited premium company interviews',
          'Google, Meta, Amazon, Netflix',
          'Advanced AI feedback',
          'Video recording',
          'Canvas diagrams',
        ]}
        cta="Subscribe"
        href="/api/payments/create-checkout?plan=premium_monthly"
        popular
      />

      {/* Pay Per Interview */}
      <PricingCard
        title="Pay As You Go"
        price="$5"
        period="/interview"
        features={[
          'Single premium interview',
          'All premium companies',
          'Full feedback report',
        ]}
        cta="Buy Credit"
        href="/api/payments/create-checkout?plan=single_interview"
      />
    </div>
  );
}
```

#### Testing Checklist
- [ ] Stripe webhook endpoint verified
- [ ] Checkout flow works for both plans
- [ ] Subscription status updates correctly
- [ ] Credits deducted on interview start
- [ ] Access gating works for premium companies
- [ ] Subscription cancellation handled
- [ ] Invoice payments processed
- [ ] Test mode works with Stripe test cards

---

## 7. Work on Evals and Smoothen/Naturalize the Interview Flow

**Priority**: HIGH | **Complexity**: HIGH

### Current State
- ✅ **Multi-agent orchestration** working (routing, intro, interview, closing)
- ✅ **Audio streaming** with barge-in support
- ✅ **Remote agent evaluation** (Google, Meta)
- ❌ **No automated eval framework** - no benchmarking system
- ❌ **Interview flow can be robotic** - lacks natural conversation flow
- ❌ **No quality metrics** - can't measure improvement

### Implementation Design

#### Evaluation Framework
**Location**: `/services/evaluation/`

```python
# evals/framework.py
from dataclasses import dataclass
from typing import List, Dict, Any
import json

@dataclass
class EvalCase:
    """A single evaluation test case"""
    id: str
    interview_type: str  # 'system_design', 'coding'
    company: str
    level: str
    question: str
    expected_topics: List[str]  # Topics that should be discussed
    rubric_criteria: Dict[str, Any]
    sample_candidate_responses: List[str]  # Simulated candidate inputs

@dataclass
class EvalResult:
    """Result of running an eval"""
    case_id: str
    success: bool
    score: float
    coverage: Dict[str, bool]  # Which topics were covered
    flow_quality: float  # How natural was the conversation
    duration_seconds: float
    transcript: str
    errors: List[str]

class EvaluationRunner:
    """Run evaluations against interview agents"""

    def __init__(self, orchestrator_url: str):
        self.orchestrator_url = orchestrator_url

    async def run_eval(self, case: EvalCase) -> EvalResult:
        """
        Run a single evaluation by simulating a candidate.
        """
        # Start interview session
        session = await self.start_session(
            company=case.company,
            interview_type=case.interview_type,
        )

        # Simulate candidate responses
        transcript = []
        start_time = time.time()

        for response in case.sample_candidate_responses:
            # Send candidate response
            agent_reply = await self.send_message(session.id, response)

            transcript.append({
                'speaker': 'candidate',
                'text': response,
            })

            transcript.append({
                'speaker': 'agent',
                'text': agent_reply.text,
            })

        duration = time.time() - start_time

        # Analyze coverage
        coverage = self._analyze_topic_coverage(
            transcript,
            case.expected_topics,
        )

        # Analyze flow quality
        flow_quality = self._analyze_flow_quality(transcript)

        # Calculate score
        score = self._calculate_score(coverage, flow_quality)

        return EvalResult(
            case_id=case.id,
            success=all(coverage.values()),
            score=score,
            coverage=coverage,
            flow_quality=flow_quality,
            duration_seconds=duration,
            transcript=json.dumps(transcript),
            errors=[],
        )

    def _analyze_topic_coverage(
        self,
        transcript: List[Dict],
        expected_topics: List[str],
    ) -> Dict[str, bool]:
        """Check if all expected topics were discussed"""
        full_text = ' '.join([msg['text'] for msg in transcript])

        coverage = {}
        for topic in expected_topics:
            # Simple keyword matching (could use embeddings for better accuracy)
            coverage[topic] = topic.lower() in full_text.lower()

        return coverage

    def _analyze_flow_quality(self, transcript: List[Dict]) -> float:
        """
        Analyze how natural the conversation flow is.
        Metrics:
        - Turn-taking balance
        - Question diversity
        - Follow-up quality
        """
        agent_turns = [msg for msg in transcript if msg['speaker'] == 'agent']

        # Check for repetitive patterns
        unique_questions = len(set([turn['text'] for turn in agent_turns]))
        total_questions = len(agent_turns)

        diversity_score = unique_questions / max(total_questions, 1)

        # Check for follow-ups (questions that reference previous context)
        follow_up_count = sum(
            1 for turn in agent_turns
            if any(word in turn['text'].lower() for word in ['you mentioned', 'earlier', 'your approach'])
        )

        follow_up_score = follow_up_count / max(total_questions, 1)

        # Combine metrics
        flow_quality = (diversity_score + follow_up_score) / 2

        return flow_quality

    def _calculate_score(
        self,
        coverage: Dict[str, bool],
        flow_quality: float,
    ) -> float:
        """Calculate overall eval score (0-10)"""
        coverage_score = sum(coverage.values()) / max(len(coverage), 1)
        return (coverage_score * 0.7 + flow_quality * 0.3) * 10

# evals/cases.py
EVAL_CASES = [
    EvalCase(
        id='google-design-url-shortener',
        interview_type='system_design',
        company='Google',
        level='Senior',
        question='Design a URL shortener like bit.ly',
        expected_topics=[
            'functional requirements',
            'scale estimation',
            'database design',
            'api design',
            'caching',
            'sharding',
        ],
        rubric_criteria={
            'requirement_gathering': 5,
            'high_level_design': 5,
            'scalability': 5,
        },
        sample_candidate_responses=[
            "I'd like to start by clarifying the requirements. Should this support custom short URLs?",
            "For scale, I'm assuming 1 billion URLs shortened per month.",
            "I'll use a key-value store like DynamoDB for storing URL mappings.",
            "For the API, I'll have POST /shorten and GET /{shortUrl} endpoints.",
            "To handle scale, I'll use Redis caching and consistent hashing for sharding.",
        ],
    ),
    # Add more eval cases...
]
```

#### Run Evals Script
```python
# scripts/run_evals.py
import asyncio
from evals.framework import EvaluationRunner
from evals.cases import EVAL_CASES

async def main():
    runner = EvaluationRunner(orchestrator_url="http://localhost:8000")

    results = []
    for case in EVAL_CASES:
        print(f"Running eval: {case.id}")
        result = await runner.run_eval(case)
        results.append(result)

        print(f"  Score: {result.score}/10")
        print(f"  Coverage: {sum(result.coverage.values())}/{len(result.coverage)}")
        print(f"  Flow Quality: {result.flow_quality:.2f}")
        print()

    # Generate report
    avg_score = sum(r.score for r in results) / len(results)
    print(f"\n=== EVAL SUMMARY ===")
    print(f"Average Score: {avg_score:.2f}/10")
    print(f"Pass Rate: {sum(r.success for r in results)}/{len(results)}")

if __name__ == "__main__":
    asyncio.run(main())
```

#### Naturalizing Interview Flow

**Problem Areas:**
1. **Robotic transitions** - agent announces phase changes
2. **Repetitive questions** - same phrasing used repeatedly
3. **Lack of context awareness** - doesn't reference candidate's previous answers
4. **Abrupt topic changes** - no smooth segues

**Solutions:**

##### 1. Improve Agent Instructions with Conversational Prompting
**Location**: `/services/interview-orchestrator/interview_orchestrator/interview_types/system_design/design_agent.py`

```python
async def design_agent_instruction(ctx):
    company = ctx.session.state.get("routing_decision", {}).get("company")
    question = ctx.session.state.get("interview_question")

    return f"""
You are a {company} senior engineer conducting a friendly, conversational system design interview.

**Question:** {question}

**Conversational Guidelines:**
1. **Be Natural:** Speak as you would to a colleague, not a script
   - Good: "That's an interesting approach! How would you handle..."
   - Bad: "Please describe how you would handle..."

2. **Build on Context:** Reference what the candidate said previously
   - "You mentioned earlier that you'd use Redis. Let's dive deeper into that..."
   - "Building on your sharding strategy, how would you..."

3. **Use Varied Phrasing:** Don't repeat questions
   - Instead of "What about X?" repeatedly, use:
     - "How might X factor into this?"
     - "X is another consideration here - what are your thoughts?"
     - "Let's explore X for a moment"

4. **Smooth Transitions:** Don't jump between topics abruptly
   - "Great! Now that we've covered the high-level design, let's drill into..."
   - "That makes sense. Another area I'd like to explore is..."

5. **Show Engagement:** React to good points
   - "Nice! That's exactly right because..."
   - "Interesting choice - I can see why you'd go that route"
   - "Good catch on considering that edge case"

6. **Ask Follow-ups:** Don't just check boxes
   - When they mention a technology, ask *why*
   - When they describe a component, ask about *trade-offs*
   - Challenge gently: "What if traffic increased 10x?"

7. **Guide, Don't Lead:** Help when stuck, but don't give answers
   - Instead of "You should use consistent hashing"
   - Say: "Think about how you'd distribute data evenly across nodes..."

**Interview Flow:**
1. Start with requirement clarification (let them drive questions)
2. Move to high-level design (let them draw, ask questions)
3. Deep dive on 2-3 components (push for details)
4. Discuss scale and trade-offs
5. Wrap up naturally

**Remember:** This should feel like a collaborative discussion, not an interrogation.
"""
```

##### 2. Add Conversational Memory
```python
# shared/conversation_memory.py
class ConversationMemory:
    """Track conversation context for more natural flow"""

    def __init__(self):
        self.mentioned_technologies = set()
        self.discussed_topics = set()
        self.candidate_decisions = []

    def extract_from_turn(self, text: str):
        """Extract key info from candidate's response"""
        # Extract technologies mentioned
        tech_keywords = ['redis', 'dynamodb', 'kafka', 'cassandra', 'kubernetes']
        for tech in tech_keywords:
            if tech in text.lower():
                self.mentioned_technologies.add(tech)

        # Extract topics
        topic_keywords = ['caching', 'sharding', 'replication', 'consistency']
        for topic in topic_keywords:
            if topic in text.lower():
                self.discussed_topics.add(topic)

    def get_context_summary(self) -> str:
        """Get summary of conversation so far"""
        return f"""
**Conversation Context:**
- Technologies mentioned: {', '.join(self.mentioned_technologies)}
- Topics discussed: {', '.join(self.discussed_topics)}
- Key decisions made: {len(self.candidate_decisions)}

Use this context to ask informed follow-up questions.
"""

# Update design_agent to use memory
design_agent = LlmAgent(
    name="design_agent",
    model=Gemini(...),
    instruction_func=lambda ctx: design_agent_instruction(ctx) + conversation_memory.get_context_summary(),
    ...
)
```

##### 3. Add Variability to Questions
```python
# shared/question_templates.py
CLARIFICATION_PHRASES = [
    "Could you elaborate on {topic}?",
    "Tell me more about your thinking around {topic}.",
    "How did you arrive at that decision for {topic}?",
    "Walk me through {topic} a bit more.",
    "{topic} is interesting - can you expand on that?",
]

TRANSITION_PHRASES = [
    "Great! Moving on,",
    "That makes sense. Another thing to consider is",
    "Perfect. Let's shift gears and talk about",
    "Good stuff. Now,",
]

def get_random_clarification(topic: str) -> str:
    import random
    template = random.choice(CLARIFICATION_PHRASES)
    return template.format(topic=topic)
```

##### 4. Reduce Meta-Commentary
```python
# Before (robotic):
"I am transferring you to the interview agent now."

# After (natural):
# Just transfer silently - coordinator shouldn't announce internal mechanics
```

#### Testing Checklist
- [ ] Eval framework runs successfully
- [ ] Eval cases cover key scenarios
- [ ] Coverage metrics accurate
- [ ] Flow quality metrics meaningful
- [ ] Agent uses varied phrasing
- [ ] Agent references previous context
- [ ] Transitions feel smooth
- [ ] No robotic announcements
- [ ] Follow-up questions are relevant

---

## 8. Add Coding Interview Flow

**Priority**: MEDIUM | **Complexity**: HIGH

### Current State
- ✅ **Coding agent skeleton** exists (`coding_interview_agent`)
- ✅ **Code executor** integrated (`BuiltInCodeExecutor`)
- ✅ **Remote agent support** available
- ❌ **No frontend UI** for code editor
- ❌ **No question bank** for coding problems
- ❌ **No test case validation**
- ❌ **Limited language support** (Python only)

### Implementation Design

#### Database Schema for Coding Questions
**Location**: `/services/frontend/db/schema/`

```typescript
// coding-questions.ts
export const difficultyLevel = pgEnum('difficulty_level', [
  'easy',
  'medium',
  'hard',
]);

export const codingQuestions = pgTable('coding_questions', {
  id: uuid('id').primaryKey().defaultRandom(),

  title: text('title').notNull(),
  slug: text('slug').notNull().unique(),
  description: text('description').notNull(),
  difficulty: difficultyLevel('difficulty').notNull(),

  // Categorization
  tags: text('tags').array(), // ['arrays', 'dynamic-programming']
  company: text('company'), // 'Google', 'Meta', etc.

  // Test Cases
  testCases: jsonb('test_cases').notNull(), // { inputs: [], expected: [] }
  hiddenTestCases: jsonb('hidden_test_cases'), // Additional test cases not shown

  // Constraints
  timeLimit: integer('time_limit').default(30), // minutes
  memoryLimit: integer('memory_limit').default(256), // MB

  // Solutions
  solutionTemplate: jsonb('solution_template'), // { python: "def solve():", js: "function solve() {}" }
  officialSolution: text('official_solution'),

  // Hints
  hints: text('hints').array(),

  // Metadata
  acceptanceRate: decimal('acceptance_rate', { precision: 5, scale: 2 }),
  totalSubmissions: integer('total_submissions').default(0),

  createdAt: timestamp('created_at').defaultNow(),
});

// coding-submissions.ts
export const codingSubmissions = pgTable('coding_submissions', {
  id: uuid('id').primaryKey().defaultRandom(),
  interviewId: uuid('interview_id').notNull().references(() => interviews.id),
  questionId: uuid('question_id').notNull().references(() => codingQuestions.id),

  code: text('code').notNull(),
  language: text('language').notNull(), // 'python', 'javascript', 'java'

  // Results
  status: text('status').notNull(), // 'accepted', 'wrong_answer', 'runtime_error', 'timeout'
  passedTests: integer('passed_tests').notNull(),
  totalTests: integer('total_tests').notNull(),

  executionTime: integer('execution_time'), // milliseconds
  memoryUsed: integer('memory_used'), // KB

  testResults: jsonb('test_results'), // Detailed results per test case

  submittedAt: timestamp('submitted_at').defaultNow(),
});
```

#### Sample Question Seed Data
```typescript
// db/seeds/coding-questions.ts
const questions: typeof codingQuestions.$inferInsert[] = [
  {
    title: 'Two Sum',
    slug: 'two-sum',
    description: `Given an array of integers nums and an integer target, return indices of the two numbers such that they add up to target.

You may assume that each input would have exactly one solution, and you may not use the same element twice.

Example:
Input: nums = [2,7,11,15], target = 9
Output: [0,1]
Explanation: nums[0] + nums[1] == 9, so we return [0, 1].`,
    difficulty: 'easy',
    tags: ['arrays', 'hash-table'],
    company: 'Google',
    testCases: {
      visible: [
        { input: { nums: [2,7,11,15], target: 9 }, expected: [0,1] },
        { input: { nums: [3,2,4], target: 6 }, expected: [1,2] },
      ],
    },
    hiddenTestCases: {
      hidden: [
        { input: { nums: [3,3], target: 6 }, expected: [0,1] },
      ],
    },
    solutionTemplate: {
      python: `def twoSum(nums, target):
    # Your code here
    pass`,
      javascript: `function twoSum(nums, target) {
    // Your code here
}`,
    },
    hints: [
      'Try using a hash map to store numbers you\'ve seen',
      'For each number, check if target - number exists in the hash map',
    ],
    timeLimit: 30,
  },
  // Add more questions...
];
```

#### Frontend Code Editor UI
**Location**: `/services/frontend/modules/interview/coding/`

```typescript
// components/code-editor.tsx
import Editor from '@monaco-editor/react';

export function CodeEditor({
  initialCode,
  language,
  onChange,
  onRun,
  onSubmit,
}: {
  initialCode: string;
  language: string;
  onChange: (code: string) => void;
  onRun: () => void;
  onSubmit: () => void;
}) {
  const [code, setCode] = useState(initialCode);

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between p-4 border-b">
        <div className="flex gap-2">
          <Select value={language}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="python">Python</SelectItem>
              <SelectItem value="javascript">JavaScript</SelectItem>
              <SelectItem value="java">Java</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex gap-2">
          <Button variant="outline" onClick={onRun}>
            Run Code
          </Button>
          <Button onClick={onSubmit}>
            Submit
          </Button>
        </div>
      </div>

      <Editor
        height="100%"
        language={language}
        value={code}
        onChange={(value) => {
          setCode(value || '');
          onChange(value || '');
        }}
        theme="vs-dark"
        options={{
          minimap: { enabled: false },
          fontSize: 14,
          lineNumbers: 'on',
          scrollBeyondLastLine: false,
        }}
      />
    </div>
  );
}

// components/test-results.tsx
export function TestResults({ results }: { results: TestResult[] }) {
  return (
    <div className="space-y-2">
      {results.map((result, i) => (
        <Card key={i} className={result.passed ? 'border-green-500' : 'border-red-500'}>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <span className="font-mono text-sm">Test Case {i + 1}</span>
              {result.passed ? (
                <CheckCircle className="text-green-500" />
              ) : (
                <XCircle className="text-red-500" />
              )}
            </div>

            <div className="mt-2 text-sm space-y-1">
              <div>
                <span className="text-muted-foreground">Input:</span>{' '}
                <code>{JSON.stringify(result.input)}</code>
              </div>
              <div>
                <span className="text-muted-foreground">Expected:</span>{' '}
                <code>{JSON.stringify(result.expected)}</code>
              </div>
              {!result.passed && (
                <div>
                  <span className="text-muted-foreground">Got:</span>{' '}
                  <code className="text-red-500">{JSON.stringify(result.actual)}</code>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// index.tsx (Coding Interview Layout)
export default function CodingInterview() {
  const { interviewId } = useInterview();
  const { data: question } = useSWR(`/api/interviews/${interviewId}/question`);

  return (
    <div className="h-screen grid grid-cols-2">
      {/* Left Panel: Question + Test Cases */}
      <div className="border-r overflow-y-auto">
        <div className="p-6 space-y-6">
          <div>
            <h1 className="text-2xl font-bold">{question?.title}</h1>
            <Badge>{question?.difficulty}</Badge>
          </div>

          <div className="prose" dangerouslySetInnerHTML={{ __html: question?.description }} />

          <Tabs>
            <TabsList>
              <TabsTrigger value="examples">Examples</TabsTrigger>
              <TabsTrigger value="hints">Hints</TabsTrigger>
            </TabsList>

            <TabsContent value="examples">
              {question?.testCases.visible.map((tc, i) => (
                <TestCaseExample key={i} testCase={tc} />
              ))}
            </TabsContent>

            <TabsContent value="hints">
              {question?.hints.map((hint, i) => (
                <Hint key={i} index={i} hint={hint} />
              ))}
            </TabsContent>
          </Tabs>
        </div>
      </div>

      {/* Right Panel: Code Editor + Results + Chat */}
      <div className="flex flex-col">
        <div className="flex-1">
          <CodeEditor
            initialCode={question?.solutionTemplate[language]}
            language={language}
            onChange={setCode}
            onRun={handleRun}
            onSubmit={handleSubmit}
          />
        </div>

        <div className="h-64 border-t">
          <Tabs defaultValue="results">
            <TabsList>
              <TabsTrigger value="results">Results</TabsTrigger>
              <TabsTrigger value="chat">Chat with Interviewer</TabsTrigger>
            </TabsList>

            <TabsContent value="results">
              <TestResults results={testResults} />
            </TabsContent>

            <TabsContent value="chat">
              <InterviewChat />
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
}
```

#### Code Execution Service
**Location**: `/services/frontend/app/api/code/`

```typescript
// execute/route.ts
export async function POST(req: Request) {
  const { code, language, questionId, testCases } = await req.json();

  // For security, run in sandboxed environment (Docker container or Lambda)
  const results = await executeCode({
    code,
    language,
    testCases,
    timeLimit: 5000, // 5s per test
    memoryLimit: 256, // 256MB
  });

  return NextResponse.json(results);
}

// lib/code-executor.ts
import Docker from 'dockerode';

const docker = new Docker();

export async function executeCode({
  code,
  language,
  testCases,
  timeLimit,
  memoryLimit,
}: {
  code: string;
  language: string;
  testCases: TestCase[];
  timeLimit: number;
  memoryLimit: number;
}): Promise<ExecutionResult[]> {
  const results: ExecutionResult[] = [];

  for (const testCase of testCases) {
    try {
      // Create container
      const container = await docker.createContainer({
        Image: `code-executor-${language}:latest`,
        Cmd: ['python', '-c', code], // Simplified
        HostConfig: {
          Memory: memoryLimit * 1024 * 1024,
          NanoCpus: 1000000000, // 1 CPU
          NetworkMode: 'none', // No network access
        },
        Env: [
          `TEST_INPUT=${JSON.stringify(testCase.input)}`,
        ],
      });

      await container.start();

      // Wait with timeout
      const timeoutPromise = new Promise((_, reject) =>
        setTimeout(() => reject(new Error('Timeout')), timeLimit)
      );

      const execPromise = container.wait();

      const result = await Promise.race([execPromise, timeoutPromise]);

      // Get output
      const logs = await container.logs({ stdout: true, stderr: true });
      const output = logs.toString();

      // Compare with expected
      const actual = JSON.parse(output.trim());
      const passed = JSON.stringify(actual) === JSON.stringify(testCase.expected);

      results.push({
        input: testCase.input,
        expected: testCase.expected,
        actual,
        passed,
        executionTime: result.time,
      });

      await container.remove();
    } catch (error) {
      results.push({
        input: testCase.input,
        expected: testCase.expected,
        actual: null,
        passed: false,
        error: error.message,
      });
    }
  }

  return results;
}
```

#### Update Coding Agent
**Location**: `/services/interview-orchestrator/interview_orchestrator/interview_types/coding/`

```python
# coding_agent.py
async def coding_agent_instruction(ctx):
    company = ctx.session.state.get("routing_decision", {}).get("company")
    question = ctx.session.state.get("interview_question")
    submissions = ctx.session.state.get("submissions", [])

    return f"""
You are a {company} senior engineer conducting a coding interview.

**Question:** {question}

**Your Role:**
1. Observe the candidate's approach as they code
2. Ask clarifying questions if they seem stuck
3. Provide hints if they're going in the wrong direction (but don't give away the answer)
4. Evaluate their:
   - Problem-solving approach
   - Code quality and organization
   - Communication while coding
   - Testing and debugging skills
   - Time/space complexity analysis

**Candidate's Progress:**
- Submissions: {len(submissions)}
- Latest status: {submissions[-1]['status'] if submissions else 'No submissions yet'}

**Guidelines:**
- Let them think through the problem first
- Ask about their approach before they start coding
- If stuck for >3 minutes, offer a hint
- After successful submission, ask about time/space complexity
- Discuss optimizations and edge cases

Be encouraging and supportive!
"""

coding_agent = LlmAgent(
    name="coding_agent",
    model=Gemini(...),
    instruction_func=coding_agent_instruction,
    tools=[code_executor, google_agent, meta_agent],
)
```

#### Testing Checklist
- [ ] Code editor loads correctly
- [ ] Syntax highlighting works for Python/JS/Java
- [ ] Code execution runs in sandboxed environment
- [ ] Test cases validated correctly
- [ ] Submit button updates interview record
- [ ] Agent provides helpful hints
- [ ] Agent evaluates approach, not just correctness
- [ ] Security: No arbitrary code execution outside sandbox
- [ ] Performance: Code execution < 5s per test

---

## Summary & Priorities

### High Priority (MVP)
1. ✅ Record audio/video and store in Vercel Blob/S3
2. ✅ Store audio transcriptions and canvas details into DB
3. ✅ Update interview record with status and details
4. ✅ Work on evals and naturalize interview flow

### Medium Priority (Post-MVP)
5. ✅ Send canvas screenshots to orchestrator and use A2A
6. ✅ Get feedback from agent and update UX
7. ✅ Add coding interview flow

### Low Priority (Growth)
8. ✅ Integrate A2P for user payments

---

## Architecture Decision Records (ADRs)

### ADR-001: Storage Provider
**Decision**: Use Vercel Blob Store for media storage
**Rationale**: Simplifies deployment, native Vercel integration, auto-CDN
**Alternative**: AWS S3 (more flexible, but requires additional setup)

### ADR-002: Code Execution
**Decision**: Use Docker containers for sandboxed code execution
**Rationale**: Security isolation, language flexibility, cost-effective
**Alternative**: AWS Lambda (simpler, but cold starts and higher cost)

### ADR-003: Payment Provider
**Decision**: Use Stripe for payments
**Rationale**: Best developer experience, comprehensive features, well-documented
**Alternative**: LemonSqueezy (simpler, but less flexible)

### ADR-004: Evaluation Framework
**Decision**: Build custom eval framework using simulated candidates
**Rationale**: Full control, integration with existing agents, cost-effective
**Alternative**: Third-party eval platforms (expensive, less customizable)

---

## Migration Plan

### Phase 1: Foundation (Week 1-2)
- [ ] Set up Vercel Blob Store / S3
- [ ] Add database schema migrations
- [ ] Implement audio/video recording storage
- [ ] Implement transcription storage

### Phase 2: Interview Quality (Week 3-4)
- [ ] Build evaluation framework
- [ ] Naturalize agent instructions
- [ ] Add conversation memory
- [ ] Improve phase transitions

### Phase 3: Feedback & Monetization (Week 5-6)
- [ ] Build feedback generation system
- [ ] Create feedback UI components
- [ ] Integrate Stripe
- [ ] Build pricing page

### Phase 4: Coding Interviews (Week 7-8)
- [ ] Seed coding question bank
- [ ] Build code editor UI
- [ ] Set up Docker-based code executor
- [ ] Update coding agent

### Phase 5: Polish & Launch (Week 9-10)
- [ ] Run comprehensive evals
- [ ] Performance optimization
- [ ] Security audit
- [ ] Beta launch
