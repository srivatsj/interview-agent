# Testing Guide for Orchestrator2 POC

This guide walks through testing the Sequential + Custom Agent patterns with:
1. `adk web` (Gemini Live UI)
2. WebSocket server (for frontend integration)
3. Automated tests (stability verification)

---

## Prerequisites

```bash
cd services/orchestrator2

# Install dependencies
uv sync --extra dev

# Set up environment
cp .env.example .env
# Add your GOOGLE_API_KEY to .env
```

---

## Test 1: ADK Web UI (Gemini Live)

The simplest way to test - uses ADK's built-in web interface.

### Start ADK Web

```bash
# Make sure you're in orchestrator2 directory
cd services/orchestrator2

# Run ADK web server
uv run adk web orchestrator2.agents.simple_interview:root_agent
```

### Access UI

1. Open browser to: `http://localhost:8000`
2. You'll see the ADK web interface

### Test Flow

**Phase 1: Intro (Sequential - Always First)**
```
You: Hi, I'm Alice and I have 5 years of experience
AI: Thanks Alice! I've noted you have 5 years of experience.
```

**Check**: Intro phase completed ✅

**Phase 2: Interview (Custom Agent - Forced Expert Calls)**
```
You: I designed a distributed caching system using Redis
AI: [Expert feedback about your design]
    Follow-up: Can you explain how this would scale to 1M users?
```

**Check**: Expert was called (see logs) ✅

```
You: I would use consistent hashing for scalability
AI: [Expert feedback again]
```

**Check**: Expert called AGAIN (forced by custom agent) ✅

**What to Observe**:
- Phases execute in ORDER (intro → interview → closing)
- Expert is called for EVERY interview response
- No prompt engineering needed!

---

## Test 2: WebSocket Server (Audio Ready)

Test the WebSocket server that's ready for frontend integration.

### Start WebSocket Server

```bash
# Terminal 1: Start server
uv run python -m orchestrator2.websocket.server

# Server starts on http://localhost:8002
```

### Test with curl

```bash
# Terminal 2: Check health
curl http://localhost:8002/health

# Expected: {"status":"healthy","service":"orchestrator2-poc"}
```

### Test with Python Client

```python
# Terminal 2: Run Python WebSocket client
uv run python << 'EOF'
import asyncio
import websockets
import json

async def test_interview():
    uri = "ws://localhost:8002/ws/test_user"

    async with websockets.connect(uri) as websocket:
        # Wait for connection message
        msg = await websocket.recv()
        print(f"Connected: {msg}")

        # Phase 1: Intro
        await websocket.send(json.dumps({
            "type": "message",
            "content": "Hi, I'm Bob with 3 years of experience"
        }))

        response = await websocket.recv()
        print(f"Intro response: {response}")

        # Phase 2: Interview (expert will be called)
        await websocket.send(json.dumps({
            "type": "message",
            "content": "I design microservices with Docker and Kubernetes"
        }))

        response = await websocket.recv()
        print(f"Interview response: {response}")

        # Get session state
        import httpx
        state = httpx.get("http://localhost:8002/session/test_user/state").json()
        print(f"\nSession state: {json.dumps(state, indent=2)}")
        print(f"Expert calls: {state.get('state', {}).get('expert_calls', 0)}")

asyncio.run(test_interview())
EOF
```

**Expected Output**:
- Connection successful ✅
- Intro response received ✅
- Interview response received ✅
- Expert calls: 1 or more ✅

---

## Test 3: Automated Stability Tests

Run the full test suite to verify patterns are stable.

### Run All Tests

```bash
# Run complete test suite
uv run pytest tests/test_simple_interview.py -v -s

# Expected:
# ✅ test_complete_flow_deterministic
# ✅ test_forced_expert_calls_every_turn
# ✅ test_state_persistence_across_phases
# ✅ test_sequential_never_skips_phases (10 runs)
# ✅ test_custom_agent_never_skips_tool (20 turns)
```

### Run Specific Tests

```bash
# Test deterministic flow
uv run pytest tests/test_simple_interview.py::TestSimpleInterviewFlow::test_complete_flow_deterministic -v -s

# Test forced tool calls
uv run pytest tests/test_simple_interview.py::TestSimpleInterviewFlow::test_forced_expert_calls_every_turn -v -s

# Test stability (10 runs)
uv run pytest tests/test_simple_interview.py::TestPatternStability::test_sequential_never_skips_phases -v -s

# Test tool calling (20 turns)
uv run pytest tests/test_simple_interview.py::TestPatternStability::test_custom_agent_never_skips_tool -v -s
```

### What Tests Verify

1. **`test_complete_flow_deterministic`**
   - Phases execute in guaranteed order
   - State persists correctly
   - Expert called in interview phase

2. **`test_forced_expert_calls_every_turn`**
   - Expert called for EVERY interview turn
   - No skipped tool calls
   - 100% reliability

3. **`test_state_persistence_across_phases`**
   - Candidate info available across phases
   - Expert uses candidate context

4. **`test_sequential_never_skips_phases`**
   - 10 runs, all execute phases in order
   - Proves determinism

5. **`test_custom_agent_never_skips_tool`**
   - 20 interview turns across 5 sessions
   - ALL turns call expert
   - Proves forced tool pattern works

---

## Test 4: Frontend Integration (Optional)

If you want to test with the actual frontend:

### Update Frontend WebSocket URL

```typescript
// In frontend, update WebSocket connection:
const ws = new WebSocket('ws://localhost:8002/ws/${userId}');
```

### Expected Behavior

1. Connect to WebSocket
2. Send audio or text messages
3. Receive responses with expert feedback
4. Interview flows: intro → interview → closing

---

## Verification Checklist

After running all tests, verify:

### Sequential Agent Pattern ✅
- [ ] Phases execute in guaranteed order (intro → interview → closing)
- [ ] No phase is skipped
- [ ] State persists across phases
- [ ] Works across 10+ runs (100% consistency)

### Custom Agent Pattern ✅
- [ ] Expert tool called for EVERY interview turn
- [ ] No tool calls are skipped
- [ ] Works across 20+ turns (100% consistency)
- [ ] No prompt engineering needed

### Audio Compatibility ✅
- [ ] Uses `gemini-2.0-flash-live-001` model
- [ ] WebSocket server handles connections
- [ ] Ready for bidirectional audio

### Stability Improvements ✅
- [ ] More reliable than LLM-based transfer/tool decisions
- [ ] Easier to debug (check code, not prompts)
- [ ] Tests are deterministic (not flaky)

---

## Logs to Monitor

### ADK Web Logs
```
✨ InterviewCustomAgent created with forced expert calls
🎯 Interview Agent: Processing 'I design...'
🔨 FORCING expert call...
🔗 Expert call #1: I design...
✅ Expert returned: Expert feedback...
🤖 Running response formatter
✅ Interview turn complete
```

### WebSocket Server Logs
```
🔌 WebSocket connected: test_user
📝 Session created for test_user
📨 Text message: type=message, content=Hi, I'm Bob...
🎯 Interview Agent: Processing 'Hi, I'm Bob...'
🔨 FORCING expert call...
✅ Response sent: Thanks Bob!...
```

### Test Logs
```
✅ Phase 1 (Intro) complete: {'candidate_name': 'Alice', ...}
✅ Phase 2 (Interview) complete: {'expert_calls': 1, ...}
✅ Turn 3 complete: Expert calls=2
✅ 10/10 runs: Phases executed in order - 100% reliability
✅ 20/20 turns called expert - 100% reliability
```

---

## Troubleshooting

### "No module named google.adk"
```bash
uv sync --extra dev
```

### "GOOGLE_API_KEY not set"
```bash
# Add to .env file:
GOOGLE_API_KEY=your-key-here
```

### Tests timing out
```bash
# Check logs for errors
uv run pytest tests/test_simple_interview.py -v -s --log-cli-level=DEBUG
```

### WebSocket connection refused
```bash
# Make sure server is running:
uv run python -m orchestrator2.websocket.server

# Check it's listening:
curl http://localhost:8002/health
```

---

## Next Steps

Once all tests pass:

1. **Compare Stability**
   - Run old orchestrator tests
   - Run new orchestrator2 tests
   - Compare pass rates

2. **Decide to Migrate**
   - If orchestrator2 is more stable → migrate
   - Keep both patterns (Sequential + Custom Agent)

3. **Update Main Orchestrator**
   - Replace coordinator with SequentialAgent
   - Replace design agent with Custom Agent
   - Update tests

---

## Success Criteria

✅ **ADK Web works**: Can complete full interview flow
✅ **WebSocket works**: Can connect and exchange messages
✅ **Tests pass**: 100% pass rate (no flaky tests)
✅ **Expert always called**: Custom agent forces tool usage
✅ **Phases in order**: Sequential agent guarantees flow

If all ✅ → Ready to migrate main orchestrator!
