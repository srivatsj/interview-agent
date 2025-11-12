# Interview Orchestrator

A real-time interview orchestration service using WebSocket and bidirectional streaming. Coordinates multi-phase interviews with specialized sub-agents for routing, introduction, interview conduct, and closing.

## Description

The Interview Orchestrator is a WebSocket-based service that manages the complete interview lifecycle:
- **Routing**: Determines interview type (coding, system design) based on candidate info
- **Introduction**: Greets candidate and explains interview format
- **Interview Conduct**: Delegates to specialized interview agents (coding or design)
- **Closing**: Wraps up interview and provides next steps

The orchestrator supports both text and audio modes with real-time bidirectional streaming for user interruption.

## Folder Structure

```
interview-orchestrator/
├── interview_orchestrator/
│   ├── __init__.py                    # Package initialization
│   ├── server.py                      # WebSocket server with FastAPI
│   ├── root_agent.py                  # Root coordinator agent
│   ├── agents/
│   │   ├── routing.py                 # Routes to interview type
│   │   ├── intro.py                   # Introduction phase agent
│   │   ├── interview.py               # Interview phase coordinator
│   │   ├── closing.py                 # Closing phase agent
│   │   └── interview_types/
│   │       ├── coding.py              # Coding interview agent
│   │       └── design.py              # System design interview agent
│   └── shared/
│       ├── schemas/                   # Data schemas
│       ├── prompts/                   # Prompt templates
│       └── agent_registry.py          # Remote agent management
├── pyproject.toml                     # Project dependencies and configuration
├── .env.example                       # Environment variable template
├── README.md                          # This file (human-readable documentation)
└── AGENTS.md                         # Agent documentation (LLM-readable)
```

## High-Level Design

```
┌────────────────────────────────────────┐
│          WebSocket Client              │
│     (Frontend / Test Client)           │
└───────────────┬────────────────────────┘
                │
                │ WebSocket (Text/Audio)
                │ Bidirectional Streaming
                ▼
┌────────────────────────────────────────┐
│      Interview Orchestrator            │
│         (port 8000)                    │
│                                        │
│  ┌──────────────────────────────────┐ │
│  │  Root Coordinator Agent          │ │
│  └──────────────┬───────────────────┘ │
│                 │                      │
│     ┌───────────┴──────────┐          │
│     ▼           ▼          ▼          │
│  ┌────────┐ ┌────────┐ ┌────────┐    │
│  │Routing │ │ Intro  │ │Closing │    │
│  │ Agent  │ │ Agent  │ │ Agent  │    │
│  └────────┘ └────────┘ └────────┘    │
│                 │                      │
│            ┌────┴─────┐               │
│            ▼          ▼               │
│       ┌────────┐ ┌──────────┐        │
│       │ Coding │ │  Design  │        │
│       │ Agent  │ │  Agent   │        │
│       └────────┘ └────┬─────┘        │
└─────────────────────────┼─────────────┘
                          │
                          │ A2A Protocol
                          ▼
             ┌──────────────────────┐
             │   Remote Agents      │
             │  - Google (8003)     │
             │  - Meta (8004)       │
             │  - Amazon (8001)     │
             │  - Uber (8002)       │
             └──────────────────────┘
```

## Setup

### 1. Install Dependencies

Using `uv` (recommended):
```bash
cd services/interview-orchestrator
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .
```

Or using `pip`:
```bash
cd services/interview-orchestrator
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
```

### 2. Configure Environment

```bash
cp .env.example .env
# Edit .env and add required configuration
```

Required environment variables:
- `GOOGLE_API_KEY`: Your Google API key for Gemini models
- `AGENT_MODEL`: (Optional) Model to use, defaults to `gemini-2.0-flash-exp`
- `REMOTE_AGENT_URLS`: (Optional) Comma-separated URLs for remote agents

## Commands to Start Service

Start the WebSocket server on port 8000:

```bash
cd services/interview-orchestrator
source .venv/bin/activate
python -m uvicorn interview_orchestrator.server:app --host 0.0.0.0 --port 8000 --reload
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

## Verify It's Running

Open your browser and navigate to:
```
http://localhost:8000
```

You should see the interview interface.

## Run Ruff (Linting and Formatting)

Check code quality:
```bash
cd services/interview-orchestrator
uv run ruff check .
```

Or:
```bash
cd services/interview-orchestrator
uv run ruff check interview_orchestrator/
```

Format code:
```bash
cd services/interview-orchestrator
uv run ruff format .
```

Fix auto-fixable issues:
```bash
cd services/interview-orchestrator
uv run ruff check . --fix
```

## WebSocket API

### Connect to WebSocket

```
ws://localhost:8000/ws
```

### Message Format

**Text Message (from client):**
```json
{
  "type": "message",
  "content": "Hello, I'm ready for the interview"
}
```

**Audio Message (from client):**
```json
{
  "type": "audio",
  "audio": "base64_encoded_audio_data"
}
```

**Server Response:**
```json
{
  "type": "text",
  "content": "Welcome to the interview..."
}
```

## Working with Remote Agents

The interview orchestrator can consume remote A2A agents (Google, Meta, Amazon, Uber) for specialized system design questions.

1. Start remote agents first (see their respective READMEs)
2. Configure agent URLs in `.env` or through agent registry
3. The design interview agent will automatically discover and use available skills

## Development

Install development dependencies:
```bash
cd services/interview-orchestrator
uv pip install -e ".[dev]"
```

This includes:
- `pytest`: Testing framework
- `pytest-asyncio`: Async test support
- `pytest-cov`: Code coverage
- `ruff`: Code linting and formatting
- `pre-commit`: Git hooks

Run tests:
```bash
cd services/interview-orchestrator
uv run pytest
```

Run tests with coverage:
```bash
cd services/interview-orchestrator
uv run pytest --cov=interview_orchestrator --cov-report=html
```

## Port Information

- **Port 8000**: Interview Orchestrator (WebSocket server)
- **Port 8001**: Google Agent (optional remote agent)
- **Port 8002**: Meta Agent (optional remote agent)

All ports must be unique when running locally.
