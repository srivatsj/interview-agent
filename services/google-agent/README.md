# Google Agent

A2A-compliant agent providing Google-style system design interviews and payment processing (AP2). Combines deterministic payment tools with LLM-based interview conductor.

## Architecture

```
Orchestrator (A2A Client)
         ↓
    HTTP/JSON (A2A Protocol)
         ↓
Google Agent (port 8001)
    ├── Custom Executor (routing)
    ├── Payment Tools (deterministic)
    │   ├── create_cart (AP2 cart mandate)
    │   └── process_payment (Stripe via frontend)
    └── Interview Tool (LLM-based)
        └── conduct_interview (multi-turn ADK agent)
```

### Three Skills

**1. create_cart_for_interview** (Deterministic)
- Creates AP2-compliant cart mandate
- Pricing: System Design ($3.00), Coding ($4.00), Behavioral ($2.50)
- JWT-signed with 15-minute expiry

**2. process_payment** (Deterministic)
- Processes AP2 payment mandate
- Forwards to Frontend Credentials Provider
- Returns payment receipt with status

**3. conduct_interview** (LLM-based)
- Multi-turn system design interview
- Google-specific feedback (scale, distributed systems, Google tech)
- ADK session management for context

## Setup

### Install
```bash
cd services/google-agent
uv venv && source .venv/bin/activate
uv pip install -e .
```

### Configure
```bash
cp .env.example .env
```

**Required Variables:**
```bash
# Google AI
GOOGLE_API_KEY=your_key_here
AGENT_MODEL=gemini-2.0-flash-exp

# Frontend (Credentials Provider)
FRONTEND_URL=http://localhost:3000

# Payment (AP2)
MERCHANT_SECRET=your_secret_here  # For JWT signing
```

### Run
```bash
uvicorn main:app --host 0.0.0.0 --port 8001
```

### Lint
```bash
uv run ruff check .
uv run ruff format .
```

## Code Structure

```
google-agent/
├── main.py                  # A2A server setup, agent card
├── agent_executor.py        # Custom executor with routing
├── utils.py                 # Message parsing helpers
└── tools/
    ├── interview_tools.py   # LLM-based interview agent
    └── payment_tools.py     # AP2 payment tools (cart + process)
```

## A2A Protocol

**Agent Card**: `http://localhost:8001/.well-known/agent-card.json`

**Skills Exposed**:
```json
{
  "skills": [
    {
      "id": "create_cart_for_interview",
      "tags": ["payment", "cart", "interview"]
    },
    {
      "id": "process_payment",
      "tags": ["payment", "ap2", "stripe"]
    },
    {
      "id": "conduct_interview",
      "tags": ["interview", "system_design", "google"]
    }
  ]
}
```

## Custom Executor

**Routing Logic** (agent_executor.py):
```python
tool_registry = {
    "create_cart": create_cart_for_interview,
    "cart": create_cart_for_interview,
    "process_payment": process_payment,
    "payment": process_payment,
    "interview": conduct_interview,
    "design": conduct_interview,
}

# Parse message → Extract command → Route to tool
command = parse_text_parts(message)[0].lower()
tool_function = tool_registry.get(command)
```

**Hybrid Pattern**:
- Deterministic tools: Fast, predictable (payment)
- LLM-based tools: Conversational, intelligent (interview)

## Payment Tools

### Cart Creation
```python
CartMandate(
    contents=CartContents(
        id="cart_google_{type}_{uuid}",
        user_cart_confirmation_required=True,
        payment_request=PaymentRequest(
            description=f"Google {interview_type} Interview",
            amount=Decimal("3.00"),  # Varies by type
            currency="USD"
        ),
        cart_expiry=(now + 15 minutes),
        merchant_name="Google Interview Platform"
    ),
    merchant_authorization=JWT_signature
)
```

**JWT Signing**:
- Algorithm: HS256
- Payload: `{cart_hash, iss, exp}`
- Secret: `MERCHANT_SECRET` environment variable

### Payment Processing
```python
# Forward to Frontend Credentials Provider
response = await httpx.post(
    f"{FRONTEND_URL}/api/payments/execute",
    json={"payment_mandate": mandate}
)

# Return receipt
PaymentReceipt(
    status="completed" | "failed",
    transaction_id=uuid,
    receipt_data={...}
)
```

## Interview Tool

**LLM Agent** (tools/interview_tools.py):
```python
interview_agent = LlmAgent(
    name="google_interviewer",
    model="gemini-2.0-flash-exp",
    instruction="""Google system design interviewer focusing on:
    - Scale: billions of users, QPS calculations
    - Distributed systems: consistency, replication, sharding, CAP
    - Google tech: Spanner, Bigtable, MapReduce
    - Production: monitoring, reliability, disaster recovery
    """
)
```

**Multi-turn Conversation**:
- Uses ADK session management (`session_id`, `user_id`)
- Returns `TaskState.input_required` to keep conversation active
- Maintains context across turns

**Interview Flow**:
1. Clarifying questions about requirements
2. High-level design guidance
3. Deep dive into components
4. Trade-offs and alternatives
5. Questions and feedback

## Google-Specific Focus

**Scale**:
- Billion-user calculations
- QPS analysis
- Storage capacity planning
- Multi-region deployment

**Distributed Systems**:
- Consistency models (Paxos/Raft, eventual consistency)
- Replication strategies (multi-region, leader-follower)
- Sharding approaches (consistent hashing, geographic)
- CAP theorem trade-offs

**Google Technologies**:
- Spanner (globally distributed SQL)
- Bigtable (NoSQL at scale)
- MapReduce patterns
- Chubby/Zookeeper

**Production Engineering**:
- Monitoring and observability
- Reliability (SLAs, SLOs)
- Disaster recovery
- Incident response

## Integration with Orchestrator

**Consumption**:
```python
# In orchestrator's interview agent
from shared.infra.a2a.remote_client import call_remote_skill

response = await call_remote_skill(
    agent_url="http://localhost:8001",
    text="conduct_interview",
    data={
        "message": "How would you design a URL shortener?",
        "user_id": "user-123",
        "session_id": "interview-456"
    }
)
# Returns: {"message": "Let's start with requirements..."}
```

**A2A Message Flow**:
```
Orchestrator
  → HTTP POST /a2a/task
  → Body: Message(text="conduct_interview", data={...})
  → Google Agent Executor
     → Parse message
     → Route to conduct_interview tool
     → Execute LLM agent
     → Return Task with artifacts
  ← Response: Task(state=input_required, artifacts=[response])
← Extract response from artifacts
```

## Inter-Service Communication

**With Orchestrator**:
- A2A Protocol: HTTP/JSON skill invocation
- Skills: `conduct_interview`, `create_cart`, `process_payment`
- Endpoints: `POST /a2a/task`, `GET /.well-known/agent-card.json`

**With Frontend**:
- Payment processing: `POST /api/payments/execute`
- Credentials Provider role in AP2 protocol

## Environment Variables

```bash
# Platform
GOOGLE_GENAI_USE_VERTEXAI=FALSE  # Use Google AI Studio

# API Key
GOOGLE_API_KEY=your_key_here

# Model
AGENT_MODEL=gemini-2.0-flash-exp

# Frontend
FRONTEND_URL=http://localhost:3000

# Payment
MERCHANT_SECRET=secret_for_jwt_signing
```

## Verify Running

**Check agent card**:
```bash
curl http://localhost:8001/.well-known/agent-card.json
```

**Test interview skill** (via orchestrator):
```python
from shared.infra.a2a.remote_client import call_remote_skill

response = await call_remote_skill(
    agent_url="http://localhost:8001",
    text="interview",
    data={"message": "Design a URL shortener", "session_id": "test-123"}
)
print(response["message"])
```

## Port Configuration

- **8001**: Google Agent (actual code)
- **8000**: Interview Orchestrator
- **3000**: Frontend (Credentials Provider)

**Note**: Documentation mentions 8003, but code uses 8001.
