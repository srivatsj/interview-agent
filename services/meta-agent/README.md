# Meta Agent

A Meta system design interview agent exposed via the A2A (Agent-to-Agent) protocol. This agent provides specialized skills for evaluating social media systems and performance optimization.

## Description

The Meta Agent is a specialized system design interview expert that helps evaluate candidates on:
- **Social Graph Design**: Architecture for social connections, news feeds, and follower systems
- **Performance Optimization**: Strategies for latency reduction, throughput improvement, and resource efficiency

## Folder Structure

```
meta-agent/
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
│  Meta Agent               │
│  (port 8002)              │
│                           │
│  Skills:                  │
│  1. Design Social Graph   │
│  2. Optimize Performance  │
└───────────────────────────┘
```

The agent exposes two specialized skills:

1. **design_social_graph**: Designs social graph architecture
   - Graph storage (adjacency lists, graph databases, sharding)
   - News feed generation (ranking, caching, fan-out strategies)
   - Performance metrics (QPS, latency targets)

2. **optimize_performance**: Suggests performance optimization strategies
   - Multi-layer caching (in-memory, Redis, CDN)
   - Database optimizations (read replicas, connection pooling, indexing)
   - Architecture patterns (async processing, load balancing, circuit breakers)
   - Monitoring and observability (metrics, tracing, auto-scaling)

## Setup

### 1. Install Dependencies

Using `uv` (recommended):
```bash
cd services/meta-agent
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
```

Or using `pip`:
```bash
cd services/meta-agent
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

Start the A2A server on port 8002:

```bash
cd services/meta-agent
source .venv/bin/activate
uvicorn agent:a2a_app --host localhost --port 8002
```

You should see:
```
INFO:     Uvicorn running on http://localhost:8002 (Press CTRL+C to quit)
```

## Verify It's Running

Check the agent card:

```bash
curl http://localhost:8002/.well-known/agent-card.json
```

You should see JSON with the agent's skills, capabilities, and description.

## Run Ruff (Linting and Formatting)

Check code quality:
```bash
cd services/meta-agent
uv run ruff check .
```

Format code:
```bash
cd services/meta-agent
uv run ruff format .
```

Fix auto-fixable issues:
```bash
cd services/meta-agent
uv run ruff check . --fix
```

## How to Consume This Agent

From another ADK agent (like interview-orchestrator), use `RemoteA2aAgent`:

```python
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH

meta_agent = RemoteA2aAgent(
    name="meta_agent",
    description="Meta system design expert for social graphs",
    agent_card=f"http://localhost:8002{AGENT_CARD_WELL_KNOWN_PATH}"
)

# Add to your coordinator's sub_agents
root_agent = Agent(
    name="coordinator",
    sub_agents=[meta_agent, ...],
    ...
)
```

## Port Information

- **Port 8002**: Meta Agent (A2A server)
- **Port 8000**: Interview orchestrator (consumes this agent)

The ports must be different when testing locally.

## Development

Install development dependencies:
```bash
cd services/meta-agent
uv pip install -e ".[dev]"
```

This includes:
- `ruff`: Code linting and formatting
