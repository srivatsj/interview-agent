# Google Agent - Agent Documentation

Quick reference for AI coding agents to understand the google-agent codebase.

## Core Architecture

**Type**: A2A-compliant agent with hybrid tool architecture
**Framework**: A2A SDK + Google ADK
**Pattern**: Custom executor with keyword routing
**Port**: 8001 (code actual, docs mention 8003)

## Entry Points

1. **main.py:15** - A2A server setup, agent card configuration
2. **agent_executor.py:23** - Custom executor with tool routing
3. **tools/interview_tools.py:18** - LLM-based interview agent
4. **tools/payment_tools.py:15** - AP2 payment tools

## Agent Card

**Location**: main.py:10

```python
AGENT_CARD = AgentCard(
    name="google_system_design_agent",
    url="http://localhost:8001",
    description="Google system design interview expert with premium feedback",
    version="1.0.0",
    skills=[...]  # 3 skills
)
```

## Skills

### 1. create_cart_for_interview (Deterministic)
**File**: tools/payment_tools.py:18
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
        id=f"cart_google_{interview_type}_{uuid}",
        user_cart_confirmation_required=True,
        payment_request=PaymentRequest(...),
        cart_expiry=(15 minutes from now),
        merchant_name="Google Interview Platform"
    ),
    merchant_authorization=JWT_signature
)
```

**JWT Signing** (payment_tools.py:45):
- SHA-256 hash of cart contents
- HS256 algorithm with `MERCHANT_SECRET`
- Payload: `{cart_hash, iss: "google_interview_platform", exp: 15min}`

### 2. process_payment (Deterministic)
**File**: tools/payment_tools.py:78
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
        "merchant": "Google Interview Platform",
        "timestamp": ...,
        "stripe_charge_id": ...  # If successful
    }
)
```

### 3. conduct_interview (LLM-based)
**File**: tools/interview_tools.py:25
**Tags**: interview, system_design, google
**Purpose**: Multi-turn system design interview

**LLM Agent**:
```python
interview_agent = LlmAgent(
    name="google_interviewer",
    model=os.getenv("AGENT_MODEL", "gemini-2.0-flash-exp"),
    instruction="""Google system design interviewer focusing on:
    - Scale: billions of users, QPS calculations
    - Distributed systems: consistency, replication, sharding, CAP
    - Google tech: Spanner, Bigtable, MapReduce
    - Production: monitoring, reliability, disaster recovery
    """
)
```

**Multi-turn**:
- Uses ADK session management: `session_id`, `user_id`
- Returns `TaskState.input_required` to continue conversation
- Maintains context via GenAI session

## Custom Executor

**File**: agent_executor.py:23

**Tool Registry** (agent_executor.py:30):
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

**Routing Logic** (agent_executor.py:45):
```python
1. Parse A2A message → text_parts, data_parts
2. Extract command from first text part
3. Match command to tool registry (keyword-based)
4. Execute tool function
5. Return task via TaskUpdater
```

**Message Parsing** (utils.py:10):
```python
parse_text_parts(message) → list[str]  # All text parts
parse_data_parts(message) → dict       # All data parts merged
```

## A2A Protocol Flow

**Request**:
```python
Message(
    message_id=uuid,
    parts=[
        Part(root=TextPart(text="interview")),  # Command
        Part(root=DataPart(data={
            "message": "Design URL shortener",
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

**Extraction** (remote_client.py in orchestrator):
- Looks for `DataPart` in `task.artifacts`
- Returns data dictionary

## Configuration

**Environment** (.env):
```bash
GOOGLE_GENAI_USE_VERTEXAI=FALSE
GOOGLE_API_KEY=your_key_here
AGENT_MODEL=gemini-2.0-flash-exp
FRONTEND_URL=http://localhost:3000
MERCHANT_SECRET=secret_for_jwt_signing
```

**Server** (main.py:40):
```python
app = A2AStarletteApplication(
    agent_card=AGENT_CARD,
    executor=GoogleAgentExecutor(),
    request_handler=DefaultRequestHandler(
        task_store=InMemoryTaskStore()
    )
)
```

## Google-Specific Focus Areas

**Scale Calculations** (instruction):
- Billion-user scenarios
- QPS analysis (read/write ratios)
- Storage capacity planning
- Bandwidth requirements
- Multi-region deployment

**Distributed Systems** (instruction):
- Consistency: Paxos/Raft, eventual consistency, CRDTs
- Replication: Multi-region, leader-follower, quorum
- Sharding: Consistent hashing, range-based, geographic
- CAP theorem trade-offs

**Google Technologies** (instruction):
- Spanner: Globally distributed SQL with external consistency
- Bigtable: NoSQL at massive scale
- MapReduce: Parallel data processing patterns
- Chubby/Zookeeper: Distributed coordination

**Production Engineering** (instruction):
- Monitoring: Metrics, logs, traces
- Reliability: SLAs, SLOs, error budgets
- Disaster recovery: Backup, failover, multi-region
- Incident response: On-call, postmortems

## Common Tasks

### Add new skill
1. Create tool function in `tools/`
2. Add to `AGENT_CARD.skills` in main.py
3. Add keyword mapping to `tool_registry` in agent_executor.py
4. Implement tool logic (deterministic or LLM-based)

### Modify pricing
1. Update `INTERVIEW_PRICES` in `tools/payment_tools.py:12`
2. Restart server

### Change interview focus
1. Edit instruction in `tools/interview_tools.py:25`
2. Restart server (ADK agents reload instruction)

### Add new payment provider
1. Modify `process_payment()` in `tools/payment_tools.py:78`
2. Update frontend URL or add new provider endpoint
3. Handle new receipt format

## Integration with Orchestrator

**Discovery** (orchestrator agent_registry.py):
```bash
# Environment variables in orchestrator
INTERVIEW_AGENTS=google,meta
GOOGLE_AGENT_URL=http://localhost:8001
GOOGLE_AGENT_TYPES=system_design,coding
```

**Call from Orchestrator** (design_agent.py):
```python
from shared.infra.a2a.remote_client import call_remote_skill

response = await call_remote_skill(
    agent_url="http://localhost:8001",
    text="interview",  # or "cart", "payment"
    data={
        "message": "Design URL shortener",
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

**Test Tools Directly**:
```python
from tools.interview_tools import conduct_interview
from a2a_sdk.task_updater import TaskUpdater

# Mock TaskUpdater
class MockUpdater:
    async def send_tool_response(self, response):
        print(response)

updater = MockUpdater()
await conduct_interview(
    data={"message": "Design URL shortener", "session_id": "test"},
    task_updater=updater
)
```

**Verify Agent Card**:
```bash
curl http://localhost:8001/.well-known/agent-card.json | jq
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

## Port Discrepancy

**Code**: Uses port 8001 (main.py:55)
**Docs**: Mentions port 8003 (README)

**Resolution**: Code takes precedence, use 8001.
