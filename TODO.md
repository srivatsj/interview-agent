# Interview Agent - Pending Features

> **Status**: Core platform implemented with system design interviews. Pending: feedback system, coding UI, payments, and evaluation framework.

---

## 🎯 High Priority

### 1. Interview Feedback System

**Status**: Not implemented
**Priority**: HIGH
**Complexity**: MEDIUM

#### What's Needed
- **Feedback database schema**
  - Overall score, category scores, rubric scores
  - Strengths/improvements arrays
  - Detailed feedback text
  - Track AI model used for generation

- **AI evaluation service**
  - Use Gemini 2.5 Pro to analyze transcripts + canvas screenshots
  - Apply rubric-based scoring
  - Generate actionable feedback
  - Support different rubrics for system design vs coding

- **Feedback UI components**
  - Overall score card (x/10)
  - Category breakdown with progress bars
  - Strengths vs improvements split view
  - Detailed rubric assessment table
  - Export functionality (PDF/JSON)

#### Database Schema (MVP)
```typescript
// services/frontend/db/schema/feedback.ts
export const feedback = product.table("feedback", {
  id: uuid("id").defaultRandom().primaryKey(),
  interviewId: uuid("interview_id").notNull().references(() => interviews.id),

  overallScore: numeric("overall_score", { precision: 4, scale: 2 }).notNull(),
  categoryScores: jsonb("category_scores").notNull(),
  rubricScores: jsonb("rubric_scores").notNull(),

  strengths: text("strengths").array().notNull(),
  improvements: text("improvements").array().notNull(),
  detailedFeedback: text("detailed_feedback"),

  generatedBy: text("generated_by").notNull().default("gemini-2.5-pro"),
  createdAt: timestamp("created_at").defaultNow().notNull(),
});
```

#### API Routes
- `POST /api/interviews/[id]/feedback` - Generate feedback
- `GET /api/interviews/[id]/feedback` - Retrieve feedback

#### UI Location
- `/services/frontend/modules/interviews/components/feedback-display.tsx`
- Shown on interview completion page or dashboard

---

### 2. Enhanced Interview Metadata

**Status**: Partially implemented (basic fields exist)
**Priority**: HIGH
**Complexity**: LOW

#### What's Needed
Expand `interviews` table with:

```typescript
// Add to services/frontend/db/schema/interviews.ts
export const interviews = product.table("interviews", {
  // ... existing fields

  // Interview details
  company: text("company"),                    // "Google", "Meta", "Free Practice"
  interviewType: text("interview_type"),       // "system_design", "coding"
  questionText: text("question_text"),         // Actual question asked
  currentPhase: text("current_phase"),         // "routing", "intro", "interview", "closing"

  // Timing
  startedAt: timestamp("started_at"),

  // Metadata
  sessionState: jsonb("session_state"),        // ADK session snapshot
});
```

#### Implementation
- Update `createInterview()` server action to accept company/type
- Sync phase updates from orchestrator to frontend DB via WebSocket events
- Display metadata on interview history page

---

### 3. Evaluation Framework

**Status**: Not implemented
**Priority**: HIGH
**Complexity**: HIGH

#### What's Needed
Build automated testing framework to measure interview quality.

#### Components

**1. Eval Runner**
```python
# services/evaluation/framework.py
class EvaluationRunner:
    async def run_eval(self, case: EvalCase) -> EvalResult:
        """Simulate candidate responses and measure agent performance."""
        - Connect to orchestrator
        - Send pre-scripted candidate responses
        - Capture agent behavior
        - Analyze topic coverage
        - Score conversation naturalness
```

**2. Eval Cases**
```python
# services/evaluation/cases/system_design.py
EVAL_CASES = [
    EvalCase(
        id="google-design-url-shortener",
        question="Design a URL shortener",
        expected_topics=["scale estimation", "database design", "caching"],
        candidate_responses=[...],  # Simulated answers
    ),
]
```

**3. Metrics**
- **Topic coverage**: Did agent cover all key areas?
- **Flow naturalness**: Smooth transitions, varied phrasing
- **Follow-ups**: Context-aware questions
- **Time efficiency**: Reasonable interview duration

**4. Run Script**
```bash
cd services/evaluation
python run_evals.py --agent=design_agent --output=report.json
```

#### Acceptance Criteria
- [ ] Can run evals against orchestrator
- [ ] Generates coverage metrics (topic checklist)
- [ ] Measures conversation naturalness (0-10 score)
- [ ] Outputs JSON report with pass/fail + scores
- [ ] CI integration for regression testing

---

## 🚧 Medium Priority

### 4. Coding Interview UI

**Status**: Agent implemented, UI not built
**Priority**: MEDIUM
**Complexity**: HIGH

#### What's Needed

**Frontend**
- Monaco code editor integration
- Language selector (Python, JavaScript, Java)
- Test case display/runner
- Real-time AI chat during coding
- Split layout: problem description | code editor + results

**Database**
```typescript
// Coding questions seed data
export const codingQuestions = product.table("coding_questions", {
  id: uuid("id").defaultRandom().primaryKey(),
  title: text("title").notNull(),
  description: text("description").notNull(),
  difficulty: text("difficulty").notNull(),  // "easy", "medium", "hard"
  testCases: jsonb("test_cases").notNull(),
  solutionTemplate: jsonb("solution_template"),
  hints: text("hints").array(),
});

// Submission tracking
export const codingSubmissions = product.table("coding_submissions", {
  id: uuid("id").defaultRandom().primaryKey(),
  interviewId: uuid("interview_id").notNull(),
  questionId: uuid("question_id").notNull(),
  code: text("code").notNull(),
  status: text("status").notNull(),  // "accepted", "wrong_answer", "timeout"
  passedTests: integer("passed_tests"),
  totalTests: integer("total_tests"),
});
```

**Code Execution**
- Use Docker containers for sandboxed execution
- Support Python, JavaScript, Java
- 5s timeout per test case
- Memory limits enforced

**UI Components**
- `/services/frontend/modules/interview/coding/components/code-editor.tsx`
- `/services/frontend/modules/interview/coding/components/test-results.tsx`
- `/services/frontend/app/interview/[id]/coding/page.tsx`

#### Acceptance Criteria
- [ ] Code editor with syntax highlighting
- [ ] Test cases run in sandboxed environment
- [ ] Results displayed (passed/failed per test)
- [ ] AI agent provides hints and evaluates approach
- [ ] Submission tracked in database

---

### 5. Naturalize Interview Conversation Flow

**Status**: Not started
**Priority**: MEDIUM
**Complexity**: MEDIUM

#### Problems to Solve
- **Robotic phrasing**: Agent uses repetitive questions
- **Abrupt transitions**: No smooth segues between topics
- **Lack of context**: Doesn't reference previous answers
- **Meta-commentary**: Announces internal phase changes

#### Solutions

**1. Improve Agent Prompts**
```python
# services/interview-orchestrator/interview_orchestrator/shared/prompts/design_agent.txt
You are a friendly senior engineer conducting a conversational interview.

Guidelines:
- Speak naturally, not from a script
- Reference what the candidate said earlier
- Use varied phrasing (avoid repeating "What about X?")
- React to good points ("Nice! That's exactly right")
- Guide, don't lead (hints instead of answers)
```

**2. Add Conversation Memory**
```python
class ConversationMemory:
    def __init__(self):
        self.mentioned_technologies = set()
        self.discussed_topics = set()

    def get_context_summary(self) -> str:
        return f"Technologies mentioned: {self.mentioned_technologies}"
```

**3. Question Templates**
```python
CLARIFICATION_PHRASES = [
    "Could you elaborate on {topic}?",
    "Tell me more about {topic}.",
    "How did you arrive at that decision?",
]

def get_random_clarification(topic: str) -> str:
    return random.choice(CLARIFICATION_PHRASES).format(topic=topic)
```

**4. Remove Meta-Commentary**
- Don't announce transfers: `"I am transferring you to the interview agent"`
- Just transfer silently

#### Acceptance Criteria
- [ ] Agent uses 5+ varied question phrasings
- [ ] Agent references candidate's previous answers
- [ ] Smooth transitions between topics
- [ ] No internal phase announcements
- [ ] Eval framework measures flow naturalness >7/10

---

### 6. Canvas Screenshots to Remote Agents

**Status**: Partially implemented (screenshots sent to orchestrator, not forwarded to remote agents)
**Priority**: MEDIUM
**Complexity**: MEDIUM

#### Current State
✅ Frontend captures canvas screenshots every 30s
✅ Screenshots sent to orchestrator via WebSocket
✅ Stored in session state
❌ NOT passed to remote agents during A2A calls

#### What's Needed

**1. Update Remote Agent Skills to Accept Images**
```python
# services/google-agent/agent.py
@FunctionTool
async def analyze_scale_requirements(
    query: str,
    diagram: dict = None,  # { mime_type: "image/png", data: "base64..." }
) -> str:
    if diagram:
        # Use Gemini 2.5 Pro Vision to analyze diagram
        parts = [
            query,
            Part(inline_data=InlineData(
                mime_type="image/png",
                data=diagram["data"]
            ))
        ]
        response = await model.generate_content_async(parts)
```

**2. Update Design Agent to Include Screenshots**
```python
# services/interview-orchestrator/interview_orchestrator/agents/interview_types/design.py
def _get_design_instruction(ctx: ReadonlyContext) -> str:
    screenshots = ctx.session.state.get("canvas_screenshots", [])
    latest = screenshots[-1] if screenshots else None

    return f"""
    The candidate is drawing on a canvas.
    Latest diagram: {"Available" if latest else "Not yet drawn"}

    When calling remote agents, include the diagram for visual analysis.
    """
```

**3. Update A2A Protocol Calls**
```python
# When calling remote agent, include screenshot
latest_screenshot = ctx.session.state.get("canvas_screenshots", [])[-1]

response = await google_agent.call_skill(
    skill_id="analyze_scale_requirements",
    inputs={
        "query": "Analyze the scale requirements",
        "diagram": {
            "mime_type": "image/png",
            "data": latest_screenshot["data"],
        }
    }
)
```

#### Acceptance Criteria
- [ ] Remote agents receive canvas screenshots
- [ ] Gemini Vision analyzes diagrams
- [ ] Feedback references visual elements
- [ ] Performance acceptable (<3s per A2A call)

---

## 💰 Low Priority

### 7. Payment Integration (Stripe)

**Status**: Not implemented
**Priority**: LOW
**Complexity**: MEDIUM

#### What's Needed

**Pricing Model**
- **Free tier**: Unlimited "Free Practice" interviews
- **Premium tier**: $29/month or $5/interview
  - Google, Meta, Amazon, Netflix companies
  - Advanced feedback with rubrics
  - Video recording downloads

**Database Schema**
```typescript
export const subscriptions = product.table("subscriptions", {
  id: uuid("id").defaultRandom().primaryKey(),
  userId: text("user_id").notNull(),
  plan: text("plan").notNull(),  // "free", "premium_monthly", "pay_per_interview"
  status: text("status").notNull(),  // "active", "canceled", "expired"

  stripeCustomerId: text("stripe_customer_id"),
  stripeSubscriptionId: text("stripe_subscription_id"),

  currentPeriodEnd: timestamp("current_period_end"),
  creditsRemaining: integer("credits_remaining").default(0),
});
```

**Implementation**
- Stripe checkout session creation
- Webhook handler for subscription events
- Feature gating middleware
- Pricing page UI
- Subscription management dashboard

#### Acceptance Criteria
- [ ] Checkout flow works for both plans
- [ ] Webhooks update subscription status
- [ ] Premium companies gated for free users
- [ ] Credits deducted on interview start
- [ ] Cancel/resume subscription working

---

## 📊 Future Enhancements

### Not Prioritized Yet

- **Interview history dashboard** with search/filter
- **Transcript export** (JSON, TXT, PDF)
- **Replay mode** using stored transcriptions + canvas snapshots
- **Behavioral interviews** (new interview type)
- **Team mode** (mock interviews with peers)
- **Performance analytics** (track improvement over time)
- **Mobile app** (React Native)

---

## 📝 Migration Status

### Completed ✅
1. Multi-agent orchestration with phase routing
2. Real-time audio streaming (Gemini Native Audio)
3. Canvas collaboration with Excalidraw
4. Video recording (canvas + webcam composite)
5. Session persistence (InMemory → PostgreSQL sync)
6. Canvas state persistence
7. A2A remote agent integration (Google, Meta)
8. Authentication (Better-Auth with OAuth)
9. Basic interview database schema

### In Progress 🚧
None currently

### Not Started ❌
1. Feedback system with AI evaluation
2. Enhanced interview metadata
3. Evaluation framework
4. Coding interview UI
5. Conversation flow naturalization
6. Canvas screenshots to remote agents
7. Payment integration

---

## 🔄 Next Steps

**Recommended order:**
1. **Interview metadata** (quick win, enables better history view)
2. **Feedback system** (core value proposition)
3. **Evaluation framework** (enables quality measurement)
4. **Conversation naturalization** (improves interview quality)
5. **Coding interview UI** (expands interview types)
6. **Payment integration** (monetization)

---

**Last Updated**: November 2024
