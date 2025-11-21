# Google Agent

A Google system design interview agent exposed via the A2A (Agent-to-Agent) protocol. This agent provides specialized skills for evaluating massive-scale distributed systems.

## Description

The Google Agent is a specialized system design interview expert that helps evaluate candidates on:
- **Massive Scale Analysis**: Calculating requirements for billion-user systems
- **Distributed Systems Design**: Recommending consistency models, replication strategies, and sharding patterns

## Folder Structure

```
google-agent/
├── __init__.py              # Package initialization
├── agent.py                 # Main agent implementation with skills
├── pyproject.toml          # Project dependencies and configuration
├── .env.example            # Environment variable template
├── README.md               # This file (human-readable documentation)
└── AGENTS.md              # Agent documentation (LLM-readable)
```

## High-Level Design

```
┌─────────────────────────┐
│ Interview Orchestrator  │
│ (or other ADK agents)   │
└───────────┬─────────────┘
            │
            │ A2A Protocol
            │ (HTTP/JSON)
            ▼
┌───────────────────────────┐
│  Google Agent             │
│  (port 8003)              │
│                           │
│  Skills:                  │
│  1. Analyze Scale         │
│  2. Design Distributed    │
│     Systems               │
└───────────────────────────┘
```

The agent exposes two specialized skills:

1. **analyze_scale_requirements**: Analyzes requirements for billion-user scale systems
   - Calculates QPS, storage, bandwidth
   - Infrastructure planning (data centers, servers)
   - Recommendations for CDN, edge caching, multi-region deployment

2. **design_distributed_systems**: Suggests distributed system architecture patterns
   - Consistency models (Paxos/Raft, CRDTs, eventual consistency)
   - Replication strategies (multi-region, leader-follower, quorum)
   - Sharding approaches (consistent hashing, range-based, geographic)
   - Design patterns (CQRS, event sourcing, saga)

## Setup

### 1. Install Dependencies

Using `uv` (recommended):
```bash
cd services/google-agent
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e . --no-verify-hashes
```

Or using `pip`:
```bash
cd services/google-agent
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY
```

Required environment variables:
- `GOOGLE_API_KEY`: Your Google API key for Gemini models
- `AGENT_MODEL`: (Optional) Model to use, defaults to `gemini-2.0-flash-exp`

## Commands to Start Service

Start the A2A server on port 8003:

```bash
cd services/google-agent
source .venv/bin/activate
uvicorn agent:a2a_app --host localhost --port 8003
```

You should see:
```
INFO:     Uvicorn running on http://localhost:8003 (Press CTRL+C to quit)
```

## Verify It's Running

Check the agent card:

```bash
curl http://localhost:8003/.well-known/agent-card.json
```

You should see JSON with the agent's skills, capabilities, and description.

## Run Ruff (Linting and Formatting)

Check code quality:
```bash
cd services/google-agent
uv run ruff check .
```

Format code:
```bash
cd services/google-agent
uv run ruff format .
```

Fix auto-fixable issues:
```bash
cd services/google-agent
uv run ruff check . --fix
```

## How to Consume This Agent

From another ADK agent (like interview-orchestrator), use `RemoteA2aAgent`:

```python
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH

google_agent = RemoteA2aAgent(
    name="google_agent",
    description="Google system design expert for massive scale",
    agent_card=f"http://localhost:8003{AGENT_CARD_WELL_KNOWN_PATH}"
)

# Add to your coordinator's sub_agents
root_agent = Agent(
    name="coordinator",
    sub_agents=[google_agent, ...],
    ...
)
```

## Port Information

- **Port 8003**: Google Agent (A2A server)
- **Port 8000**: Interview orchestrator (consumes this agent)

The ports must be different when testing locally.

## Development

Install development dependencies:
```bash
cd services/google-agent
uv pip install -e ".[dev]"
```

This includes:
- `ruff`: Code linting and formatting
