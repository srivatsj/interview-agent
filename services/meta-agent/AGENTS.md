# Meta Agent - Agent Documentation

Quick reference for AI coding agents to understand the meta-agent codebase.

## Core Architecture

**Type**: A2A-compliant agent with hybrid tool architecture
**Framework**: A2A SDK + Google ADK
**Pattern**: Custom executor with keyword routing
**Port**: 8002

## Entry Points

1. **main.py** - A2A server setup, agent card configuration
2. **agent_executor.py** - Custom executor with tool routing
3. **tools/interview_tools.py** - LLM-based interview agent
4. **tools/payment_tools.py** - AP2 payment tools

## Agent Card

**Location**: main.py

```python
AGENT_CARD = AgentCard(
    name="meta_system_design_agent",
    url="http://localhost:8002",
    description="Meta system design interview expert for social graphs and performance optimization",
    version="1.0.0",
    skills=[...]  # 3 skills
)
```

## Skills

### 1. create_cart_for_interview (Deterministic)
**File**: tools/payment_tools.py
**Tags**: payment, cart, interview
**Purpose**: Creates AP2-compliant cart mandate

**Pricing**:
```python
INTERVIEW_PRICES = {
    "system_design": Decimal("3.00"),
    "coding": Decimal("4.00"),
    "behavioral": Decimal("2.50")
}
```

**Cart Structure**:
```python
CartMandate(
    contents=CartContents(
        id=f"cart_meta_{interview_type}_{uuid}",
        user_cart_confirmation_required=True,
        payment_request=PaymentRequest(...),
        cart_expiry=(15 minutes from now),
        merchant_name="Meta Interview Platform"
    ),
    merchant_authorization=JWT_signature
)
```

**JWT Signing**:
- SHA-256 hash of cart contents
- HS256 algorithm with `MERCHANT_SECRET`
- Payload: `{cart_hash, iss: "meta_interview_platform", exp: 15min}`

### 2. process_payment (Deterministic)
**File**: tools/payment_tools.py
**Tags**: payment, ap2, stripe
**Purpose**: Processes payment via Frontend Credentials Provider

**Flow**:
```python
1. Receive payment mandate from orchestrator
2. Forward to frontend: POST {FRONTEND_URL}/api/payments/execute
3. Frontend creates Stripe charge
4. Return payment receipt with status
```

**Receipt**:
```python
PaymentReceipt(
    status="completed" | "failed",
    transaction_id=uuid,
    receipt_data={
        "amount": ...,
        "currency": "USD",
        "merchant": "Meta Interview Platform",
        "timestamp": ...,
        "stripe_charge_id": ...  # If successful
    }
)
```

### 3. conduct_interview (LLM-based)
**File**: tools/interview_tools.py
**Tags**: interview, system_design, meta
**Purpose**: Multi-turn system design interview

**LLM Agent**:
```python
interview_agent = LlmAgent(
    name="meta_interviewer",
    model=os.getenv("AGENT_MODEL", "gemini-2.0-flash-exp"),
    instruction="""Meta system design interviewer focusing on:
    - Social graphs: friend connections, news feeds, followers
    - Performance: latency reduction, caching strategies
    - Optimization: database query optimization, resource efficiency
    - Real-time systems: live updates, notifications
    """
)
```

**Multi-turn**:
- Uses ADK session management: `session_id`, `user_id`
- Returns `TaskState.input_required` to continue conversation
- Maintains context via GenAI session

## Custom Executor

**File**: agent_executor.py

**Tool Registry**:
```python
self.tool_registry = {
    "create_cart": create_cart_for_interview,
    "cart": create_cart_for_interview,
    "process_payment": process_payment,
    "payment": process_payment,
    "interview": conduct_interview,
    "design": conduct_interview,
}
```

**Routing Logic**:
```python
1. Parse A2A message → text_parts, data_parts
2. Extract command from first text part
3. Match command to tool registry (keyword-based)
4. Execute tool function
5. Return task via TaskUpdater
```

## A2A Protocol Flow

**Request**:
```python
Message(
    message_id=uuid,
    parts=[
        Part(root=TextPart(text="interview")),  # Command
        Part(root=DataPart(data={
            "message": "Design Instagram feed",
            "user_id": "...",
            "session_id": "..."
        }))
    ],
    role=Role.agent
)
```

**Response**:
```python
Task(
    task_id=uuid,
    state=TaskState.input_required,  # Continue conversation
    artifacts=[
        Part(root=DataPart(data={
            "message": "Let's start with requirements..."
        }))
    ]
)
```

## Configuration

**Environment** (.env):
```bash
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_API_KEY=your_key_here
AGENT_MODEL=gemini-2.0-flash-exp
FRONTEND_URL=http://localhost:3000
MERCHANT_SECRET=secret_for_jwt_signing
```

**Server** (main.py):
```python
app = A2AStarletteApplication(
    agent_card=AGENT_CARD,
    executor=MetaAgentExecutor(),
    request_handler=DefaultRequestHandler(
        task_store=InMemoryTaskStore()
    )
)
```

## Meta-Specific Focus Areas

**Social Graph Design**:
- Friend connections and asymmetric relationships (followers)
- News feed ranking algorithms
- Graph storage (adjacency lists, graph databases)
- Fan-out strategies (push, pull, hybrid)

**Performance Optimization**:
- Caching strategies (Redis, Memcached)
- Database query optimization
- API latency reduction (< 100ms P99)
- Load balancing and auto-scaling

**Real-time Systems**:
- WebSocket connections for live updates
- Notification systems
- Presence indicators (online/offline status)
- Real-time messaging

**Meta Technologies**:
- TAO: Social graph data store
- Memcache: Distributed caching
- Haystack: Photo storage optimization
- React: Frontend performance

## Common Tasks

### Add new skill
1. Create tool function in `tools/`
2. Add to `AGENT_CARD.skills` in main.py
3. Add keyword mapping to `tool_registry` in agent_executor.py
4. Implement tool logic (deterministic or LLM-based)

### Modify pricing
1. Update `INTERVIEW_PRICES` in `tools/payment_tools.py`
2. Restart server

### Change interview focus
1. Edit instruction in `tools/interview_tools.py`
2. Restart server (ADK agents reload instruction)

## Integration with Orchestrator

**Discovery** (orchestrator agent_registry.py):
```bash
# Environment variables in orchestrator
INTERVIEW_AGENTS=google,meta
META_AGENT_URL=http://localhost:8002
META_AGENT_TYPES=system_design
```

**Call from Orchestrator**:
```python
from shared.infra.a2a.remote_client import call_remote_skill

response = await call_remote_skill(
    agent_url="http://localhost:8002",
    text="interview",
    data={
        "message": "Design Instagram feed",
        "user_id": "user-123",
        "session_id": "interview-456"
    }
)
# Returns: {"message": "..."}
```

## Debugging

**Enable A2A Logging**:
```python
# In main.py
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Verify Agent Card**:
```bash
curl http://localhost:8002/.well-known/agent-card.json | jq
```

## Dependencies

**Core**:
- `a2a-sdk>=0.3.0`: A2A protocol
- `ap2`: Payment protocol
- `google-adk>=1.17.0`: Agent framework
- `httpx>=0.27.0`: HTTP client
- `PyJWT>=2.8.0`: JWT signing
- `uvicorn[standard]>=0.32.0`: ASGI server

**Dev**:
- `ruff>=0.8.4`: Linting/formatting
