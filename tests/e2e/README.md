# E2E Test Suite for Interview Agent

## Overview
End-to-end tests for the Interview Agent platform, covering both the Google Agent (A2A) and Orchestrator (WebSocket) layers.

## Test Results Summary

```
✅ 6 PASSED
⏱️  Total Time: 65.10s (~1 min 5 sec)
📊 Pass Rate: 100%
```

---

## Quick Start

```bash
# Run all E2E tests
cd tests
source .venv/bin/activate
pytest e2e/ -v
```

**Expected output**: ✅ 6 PASSED in ~65 seconds

---

## Test Files

| File | Purpose | Tests |
|------|---------|-------|
| `test_full_interview.py` | Remote Agent A2A Protocol | 4 tests |
| `test_orchestrator_websocket.py` | Orchestrator WebSocket + State | 2 tests |
| `conftest.py` | Pytest fixtures (server startup, cleanup, debug helpers) |
| `a2a_helper.py` | A2A client for remote agent testing |
| `websocket_helper.py` | WebSocket test client for orchestrator |

---

## Test Details

### A. Remote Agent (A2A) Tests - `test_full_interview.py`

Tests the Google interview agent directly via A2A protocol (bypassing orchestrator).

#### 1. `test_google_agent_direct_call` ✅
**Tests:** Basic A2A communication
**Coverage:** Agent card fetching, JSON-RPC invocation, single response
**Multi-turn:** No
**Canvas:** No
**State:** No

---

#### 2. `test_google_agent_multi_turn` ✅
**Tests:** Conversation context persistence
**Coverage:** 3-turn conversation with same session_id
**Multi-turn:** ✅ 3 turns
**Canvas:** No
**State:** Session persistence only

**Turns:**
1. "Hi, I'm ready"
2. "I'd like to clarify the requirements"
3. "I propose using Spanner and Bigtable"

---

#### 3. `test_system_design_interview_with_png` ✅
**Tests:** PNG canvas diagram processing
**Coverage:** Multi-turn with architecture diagram, context after canvas
**Multi-turn:** ✅ 3 turns
**Canvas:** ✅ PNG (system design whiteboard, 47KB)
**State:** No

**Turns:**
1. Share architecture PNG + text
2. Discuss caching strategy
3. Scale discussion

---

#### 4. `test_coding_interview_with_text` ✅
**Tests:** Text code processing
**Coverage:** Multi-turn with code as text, context after code
**Multi-turn:** ✅ 3 turns
**Canvas:** ✅ Text (Python code, 2KB)
**State:** No

**Turns:**
1. Share Python implementation as text
2. Discuss encoding strategy
3. Edge cases discussion

---

### B. Orchestrator (WebSocket + State) Tests - `test_orchestrator_websocket.py`

Tests the complete system via WebSocket (frontend → orchestrator → remote agent) with state verification.

#### 5. `test_phase_transitions_routing_to_design` ✅
**Tests:** Phase flow with state transitions and tool calls
**Coverage:** routing → payment → intro → interview phases
**Multi-turn:** ✅ 6 turns (intro uses 4 turns to collect candidate info)
**Canvas:** No
**State:** ✅ Full state verification at each phase

**Phase Flow:**
1. **Routing:** "Hello, I want to practice interviews" → phase=routing
2. **Payment:** "I'd like a Google system design interview" → phase=intro, payment_completed=true
3-6. **Intro (4 turns):** Collect name, years, domain, projects → phase=interview

**State Assertions:**
- `interview_phase`: routing → intro → interview
- `payment_completed`: true
- `routing_decision`: {company: "google", interview_type: "system_design"}
- `candidate_info`: {name, years_experience, domain, projects}

**Tool Call Verification:**
- `confirm_company_selection`
- `save_candidate_info`

---

#### 6. `test_full_e2e_with_design_and_closing` ✅
**Tests:** Complete critical user journey with canvas
**Coverage:** All phases including design with PNG canvas and closing
**Multi-turn:** ✅ 9 turns total
**Canvas:** ✅ PNG sent during design, verified in state
**State:** ✅ Full state + canvas persistence

**Phase Flow:**
1-2. Routing + Payment
3-6. Intro (4 turns to collect candidate info)
7. Design Turn 1: Send PNG canvas + text
8. Design Turn 2: Discuss database (canvas persists in state)
9. Closing: "I think I'm done"

**State Assertions:**
- All phases complete
- `canvas_screenshot`: base64 PNG persists across turns
- Payment and candidate info verified
- Tool calls verified

---

## Test Coverage Matrix

| Feature | Test 1 | Test 2 | Test 3 | Test 4 | Test 5 | Test 6 |
|---------|:------:|:------:|:------:|:------:|:------:|:------:|
| **A2A Protocol** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Multi-turn** | ❌ | ✅(3) | ✅(3) | ✅(3) | ✅(6) | ✅(9) |
| **Phase Transitions** | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| **State Verification** | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| **Payment Flow** | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| **Candidate Info** | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| **Tool Calls** | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| **Canvas PNG** | ❌ | ❌ | ✅ | ❌ | ❌ | ✅ |
| **Canvas Text** | ❌ | ❌ | ❌ | ✅ | ❌ | ❌ |
| **Canvas Persistence** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **Closing Phase** | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ |
| **WebSocket** | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |

**Legend:**
- Tests 1-4: Remote agent only (A2A direct)
- Tests 5-6: Full stack (WebSocket → Orchestrator → Remote agent)
- ✅(n): Number indicates conversation turns

---

## Running Tests

### All Tests
```bash
cd tests
source .venv/bin/activate
pytest e2e/ -v
```

### By Test File
```bash
# Remote agent tests only (4 tests)
pytest e2e/test_full_interview.py -v

# Orchestrator tests only (2 tests)
pytest e2e/test_orchestrator_websocket.py -v
```

### Single Test
```bash
pytest e2e/test_orchestrator_websocket.py::TestOrchestratorCriticalUserJourneys::test_phase_transitions_routing_to_design -v
```

### With Debugging
```bash
# Show print statements and logs
pytest e2e/ -v -s --log-cli-level=INFO

# Stop on first failure
pytest e2e/ -v -x
```

---

## Test Infrastructure

### Server Fixtures (`conftest.py`)

**`google_agent_server`** (session-scoped)
- Starts Google agent on port 8001
- Health check via `.well-known/agent-card.json`
- Subprocess with temp log files
- Auto-cleanup on teardown

**`orchestrator_server`** (session-scoped)
- Starts orchestrator on port 8000
- Uses orchestrator's .venv Python
- Sets ENV=test, AUTO_APPROVE_PAYMENTS=true
- Uses test DATABASE_URL from tests/.env
- Health check via `/health`
- Subprocess with temp log files
- Auto-cleanup + database cleanup on teardown

**`get_session`** (function-scoped)
- Debug fixture to query session state
- Returns `{state: {}, tool_calls: []}`
- Used for state assertions in tests

### Environment Configuration

**Test Mode** (tests/.env):
```bash
ENV=test
AUTO_APPROVE_PAYMENTS=true
DATABASE_URL=postgresql://... # Test database
GEMINI_MODEL=gemini-2.5-flash-exp
```

**Features:**
- Text-only mode (no speech_config)
- Payment auto-approval
- Test database isolation
- Fast model for testing

---

## Canvas Data

### Test Fixtures (`../canvas_data/`)

| File | Type | Size | Used In |
|------|------|------|---------|
| `system_design_whiteboard.png` | PNG | 47KB | Test 3, Test 6 |
| `code_implementation.txt` | Text | 2KB | Test 4 |

### Canvas Strategy

| Interview Type | Format | Rationale |
|----------------|--------|-----------|
| System Design  | PNG    | Visual architecture, spatial layout |
| Coding         | Text   | Precise parsing, 10-100x cheaper, faster |

---

## Key Features Tested

### ✅ A2A Protocol
- Agent card discovery
- JSON-RPC skill invocation
- Session persistence
- Multi-turn conversations

### ✅ WebSocket Communication
- Bidirectional streaming
- Text message handling
- Connection lifecycle
- Message format validation

### ✅ Phase Transitions
- routing → payment → intro → interview → closing
- State changes at each phase
- Tool calls at transitions
- Payment auto-approval

### ✅ State Management
- Session state persistence
- Candidate info storage
- Routing decision storage
- Canvas screenshot persistence

### ✅ Tool Calls
- `confirm_company_selection`
- `save_candidate_info`
- Extraction from ADK session events

### ✅ Canvas Handling
- PNG image (base64) for system design
- Text content for coding
- Canvas persistence across turns

---

## Architecture Verified

```
┌─────────────────────────────────────────────────────────┐
│                    E2E Test Suite                       │
│                   6 tests, 100% pass                    │
└─────────────────────────────────────────────────────────┘
                          │
        ┌─────────────────┴──────────────────┐
        ▼                                     ▼
┌──────────────────┐              ┌─────────────────────┐
│   A2A Tests      │              │  WebSocket Tests    │
│   (Tests 1-4)    │              │  (Tests 5-6)        │
└────────┬─────────┘              └──────────┬──────────┘
         │                                   │
         ▼                                   ▼
┌─────────────────────┐          ┌──────────────────────┐
│  Google Agent       │◄─────────│  Orchestrator        │
│  (localhost:8001)   │   A2A    │  (localhost:8000)    │
│                     │  calls   │                      │
│  - conduct_interview│          │  - WebSocket Server  │
│  - Session Store    │          │  - Phase Routing     │
│  - ADK              │          │  - State Management  │
└─────────────────────┘          └──────────────────────┘
         │                                   │
         └───────────────┬───────────────────┘
                         ▼
                ┌─────────────────┐
                │  Neon Database  │
                │  (Test DB)      │
                └─────────────────┘
```

---

## Debugging

### Check Subprocess Logs

Tests write subprocess stdout/stderr to temp files. On failure, logs are available in error output.

### Manual Server Testing

```bash
# Terminal 1: Start orchestrator
cd services/interview-orchestrator
source .venv/bin/activate
ENV=test AUTO_APPROVE_PAYMENTS=true python -m uvicorn interview_orchestrator.server:app --port 8000

# Terminal 2: Start Google agent
cd services/google-agent
uvicorn main:app --port 8001

# Terminal 3: Run tests with verbose output
cd tests
source .venv/bin/activate
pytest e2e/ -v -s --log-cli-level=INFO
```

### Common Issues

**Session not found**
- Session removed from `active_sessions` when WebSocket closes
- Use `get_session` fixture BEFORE closing WebSocket
- Check for tool call errors that crash agent task

**Tests timeout**
- Check model is responding (GEMINI_MODEL in .env)
- Increase timeout in websocket_helper.py
- Check for agent infinite loops

---

## Success Criteria

✅ **6/6 tests passing** - All critical paths verified
✅ **State verification** - Phase transitions tracked
✅ **Tool call verification** - Agent actions confirmed
✅ **Canvas support** - Both PNG and text working
✅ **Multi-turn** - Context maintained across conversations
✅ **Payment flow** - Auto-approval functional
✅ **Clean teardown** - No resource leaks

**Total: 100% pass rate**
