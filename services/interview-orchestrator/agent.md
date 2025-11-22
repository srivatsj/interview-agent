# Interview Orchestrator - Agent Documentation

Quick reference for AI coding agents to understand the interview-orchestrator codebase.

## Core Architecture

**Type**: Multi-agent WebSocket service
**Framework**: Google ADK 1.16.0 + FastAPI
**Pattern**: Phase-based routing with InMemory sessions
**Database**: PostgreSQL (sync on disconnect)

## Entry Points

1. **server.py:10** - Main entry, delegates to `websocket.app`
2. **websocket/app.py:67** - FastAPI app, WebSocket endpoint `/ws/{user_id}`
3. **root_agent.py:13** - Root coordinator with dynamic instruction

## Agent Hierarchy

```python
root_agent (interview_coordinator)
├── routing_agent        # session.state["interview_phase"] = "routing"
├── intro_agent         # session.state["interview_phase"] = "intro"
├── interview_agent     # session.state["interview_phase"] = "interview"
│   ├── design_interview_agent
│   └── coding_interview_agent
└── closing_agent       # session.state["interview_phase"] = "closing"
```

**Phase Transitions**:
- routing → intro: After payment confirmed, routing_decision saved
- intro → interview: After candidate_info saved
- interview → closing: After interview marked complete
- closing → done: After interview_complete flag set

## Key Files

### WebSocket Layer
- **websocket/app.py:67** - `websocket_endpoint()` - Main WS handler
- **websocket/session.py:21** - `start_agent_session()` - Creates InMemoryRunner
- **websocket/session.py:74** - `sync_session_to_database()` - PostgreSQL sync
- **websocket/events.py:8** - `should_sync_event()` - Filters to text-only
- **websocket/agent_to_client.py:23** - Streams agent → client
- **websocket/client_to_agent.py:16** - Relays client → agent

### Agents
- **root_agent.py:38** - `_get_coordinator_instruction()` - Phase router
- **agents/routing.py:89** - `confirm_company_selection()` - Payment tool
- **agents/intro.py:47** - `save_candidate_info()` - Saves to state
- **agents/interview.py:19** - Non-conversational router
- **agents/interview_types/design.py:70** - `ask_remote_expert()` - A2A call
- **agents/interview_types/coding.py:73** - Code executor + remote expert
- **agents/closing.py:39** - `mark_interview_complete()` - Transitions to done

### Infrastructure
- **shared/infra/a2a/agent_registry.py:16** - Remote agent discovery
- **shared/infra/a2a/remote_client.py:54** - A2A protocol client
- **shared/infra/ap2/payment_flow.py:18** - AP2 payment orchestration
- **shared/infra/ap2/cart_helpers.py:11** - Cart mandate retrieval

## Session State Schema

```python
session.state = {
    # Core (set at start)
    "user_id": str,
    "interview_id": str,
    "session_key": str,

    # Phase management
    "interview_phase": "routing" | "intro" | "interview" | "closing" | "done",

    # Payment (routing phase)
    "pending_confirmation": {...},  # Temporary UI state
    "payment_completed": bool,
    "payment_proof": {...},

    # Routing (after payment)
    "routing_decision": {
        "company": str,
        "interview_type": str,
        "confidence": float
    },

    # Candidate (intro phase)
    "candidate_info": {
        "name": str,
        "years_experience": int,
        "domain": str,
        "projects": str
    },

    # Completion
    "interview_complete": bool
}
```

## Message Flow

**Client → Server** (client_to_agent.py):
```python
{"mime_type": "audio/pcm", "data": "base64"}  # Audio chunk
{"mime_type": "text/plain", "data": "Hello"}  # Text message
{"mime_type": "confirmation_response", "data": {...}}  # Payment confirm
```

**Server → Client** (agent_to_client.py):
```python
{
    "author": "agent",
    "is_partial": bool,
    "turn_complete": bool,
    "interrupted": bool,
    "parts": [{"type": "audio/pcm" | "text", "data": ...}],
    "state": {...}  # Current session state
}
```

## A2A Integration

**Discovery** (agent_registry.py):
```python
AgentProviderRegistry.get_agent_url("google", "system_design")
→ http://localhost:8001
```

**Call** (remote_client.py:103):
```python
await call_remote_skill(
    agent_url="http://localhost:8001",
    text="Conduct interview",
    data={"message": "...", "session_id": "..."}
)
```

**Multi-turn**: Uses `session_id` for context, remote agent returns `TaskState.input_required`

## Payment Flow

1. **Get cart** (cart_helpers.py:11):
   ```python
   cart_mandate = await get_cart_mandate(agent_url, company, interview_type)
   ```

2. **Show UI**: Set `pending_confirmation` → Frontend displays payment

3. **User confirms**: Client sends `confirmation_response` → payment_flow.py:18

4. **Execute**:
   ```python
   token = await _get_payment_token(user_id, cart_mandate)  # From frontend
   mandate = _create_payment_mandate(cart, token, ...)
   receipt = await _charge_via_merchant(agent_url, mandate)
   ```

5. **Complete**: Store `payment_proof`, transition to `intro`

## Database Sync

**Optimization** (events.py:8):
- Filter to text transcriptions only (no audio chunks)
- Reduces sync time: 50 minutes → 2 minutes

**Enrichment** (events.py:24):
- Copy transcriptions into `event.content.parts[]`
- ADK only persists `content` field

**Sync** (session.py:74):
- Create DatabaseSessionService with PostgreSQL URL
- Batch sync in 50-event chunks
- Uses `asyncio.gather()` for parallel writes

## Configuration

**Environment** (.env):
```bash
GOOGLE_API_KEY=...                              # Required
AGENT_MODEL=gemini-2.5-flash-native-audio-...   # Audio model
DATABASE_URL=postgresql://...                   # Required
FRONTEND_URL=http://localhost:3000              # For AP2
INTERVIEW_AGENTS=google,meta                    # Remote agents
GOOGLE_AGENT_URL=http://localhost:8001
GOOGLE_AGENT_TYPES=system_design,coding
```

**Model** (shared/constants.py:11):
```python
Gemini(
    model=os.getenv("AGENT_MODEL"),
    speech_config=SpeechConfig(language_code="en-US", voice_name="Kore")
)
```

## Common Tasks

### Add new agent phase
1. Create agent file in `agents/`
2. Add phase constant to root_agent.py
3. Update `_get_coordinator_instruction()` with new case
4. Add transition logic in previous phase's tools

### Add remote agent
1. Update `.env`:
   ```bash
   INTERVIEW_AGENTS=google,meta,newagent
   NEWAGENT_AGENT_URL=http://localhost:8005
   NEWAGENT_AGENT_TYPES=system_design
   ```
2. Registry auto-discovers via environment variables

### Modify session state
1. Update state in agent tool: `tool_context.state[key] = value`
2. State propagates to all agents
3. Sent to client in `state` field of agent messages

### Add WebSocket message type
1. Add handler in `client_to_agent.py:16` (mime_type switch)
2. Convert to ADK LiveContent format
3. Send via `live_request_queue.put()`

## Debugging

**Session State**: Check `websocket/agent_to_client.py:96` for state serialization
**Event Filtering**: Add logging in `websocket/events.py:8`
**A2A Calls**: Check `shared/infra/a2a/remote_client.py:54` for request/response
**Payment**: Enable logging in `shared/infra/ap2/payment_flow.py:18`

## Testing

**Run all tests**:
```bash
uv run pytest tests/
```

**Test specific module**:
```bash
uv run pytest tests/interview_types/system_design/test_design_agent_tool.py -v
```

**Coverage**:
```bash
uv run pytest --cov=interview_orchestrator --cov-report=html
```
