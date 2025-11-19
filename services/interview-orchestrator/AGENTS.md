# Interview Orchestrator - LLM Documentation

## Service Specification

**Name:** `interview_orchestrator`
**Type:** WebSocket Service with Multi-Agent Orchestration
**Port:** 8000
**Protocol:** WebSocket (bidirectional streaming)
**Endpoint:** `ws://localhost:8000/ws`

## Overview

The Interview Orchestrator is a stateful, multi-phase interview coordination service that manages the complete interview lifecycle through specialized sub-agents. It uses Google ADK's agent framework with bidirectional streaming for real-time interaction.

## Architecture

### Agent Hierarchy

```
root_agent (interview_coordinator)
├── routing_agent          # Determines interview type
├── intro_agent           # Introduction and greeting
├── interview_agent       # Interview conductor
│   ├── coding_agent     # For coding interviews
│   └── design_agent     # For system design interviews
│       └── Remote A2A Agents (optional)
│           ├── google_agent (port 8003)
│           ├── meta_agent (port 8004)
│           ├── amazon_agent (port 8001)
│           └── uber_agent (port 8002)
└── closing_agent         # Interview wrap-up
```

### State Machine

The orchestrator uses a state-based flow:

```
START
  ↓
routing (determines interview type)
  ↓
intro (greets candidate)
  ↓
interview (conducts interview)
  ↓
closing (wraps up)
  ↓
done (session complete)
```

## Agent Specifications

### 1. Root Coordinator Agent

**Name:** `interview_coordinator`
**Role:** State-based routing coordinator
**Model:** Configurable via `AGENT_MODEL` (default: `gemini-2.0-flash-exp`)

**State-Based Routing Logic:**
```python
phase = session.state.get("interview_phase", "routing")

if phase == "routing":
    transfer_to(routing_agent)
elif phase == "intro":
    transfer_to(intro_agent)
elif phase == "interview":
    transfer_to(interview_agent)
elif phase == "closing":
    transfer_to(closing_agent)
else:  # done
    end_session()
```

### 2. Routing Agent

**Name:** `routing_agent`
**Purpose:** Determine interview type based on candidate information

**Input:** Candidate information (name, role, company)
**Output:** Sets `interview_type` in session state (`"coding"` or `"design"`)

**State Transitions:**
- Sets `interview_type` to `"coding"` or `"design"`
- Sets `interview_phase` to `"intro"`
- Transfers control to intro_agent

### 3. Intro Agent

**Name:** `intro_agent`
**Purpose:** Greet candidate and explain interview format

**Responsibilities:**
- Welcome candidate by name
- Explain interview structure
- Set expectations
- Build rapport

**State Transitions:**
- Sets `interview_phase` to `"interview"`
- Transfers control to interview_agent

### 4. Interview Agent

**Name:** `interview_agent`
**Purpose:** Coordinate the actual interview based on type

**Sub-Agents:**

#### 4a. Coding Agent
**Name:** `coding_agent`
**Active when:** `interview_type == "coding"`

**Responsibilities:**
- Ask coding problems
- Evaluate problem-solving approach
- Assess code quality and optimization
- Test edge cases

#### 4b. Design Agent
**Name:** `design_agent`
**Active when:** `interview_type == "design"`

**Responsibilities:**
- Ask system design questions
- Evaluate architectural decisions
- Assess scalability considerations
- Use remote agents for specialized evaluation

**Remote Agent Integration:**
The design agent can consume remote A2A agents for specialized evaluation:
- **google_agent**: Massive scale and distributed systems
- **meta_agent**: Social graphs and performance optimization
- **amazon_agent**: AWS architecture and capacity planning
- **uber_agent**: Ride-sharing systems and matching algorithms

**State Transitions:**
- Sets `interview_phase` to `"closing"`
- Transfers control to closing_agent

### 5. Closing Agent

**Name:** `closing_agent`
**Purpose:** Wrap up interview and provide next steps

**Responsibilities:**
- Thank candidate
- Explain next steps in process
- Answer final questions
- End session gracefully

**State Transitions:**
- Sets `interview_phase` to `"done"`
- Returns to root coordinator for session end

## WebSocket Protocol

### Connection

```
ws://localhost:8000/ws
```

### Message Types

#### Client → Server

**Text Message:**
```json
{
  "type": "message",
  "content": "Hello, I'm ready for the interview"
}
```

**Audio Message:**
```json
{
  "type": "audio",
  "audio": "<base64_encoded_audio_data>"
}
```

**Metadata Message:**
```json
{
  "type": "metadata",
  "user_id": "candidate_123",
  "is_audio": false
}
```

#### Server → Client

**Text Response:**
```json
{
  "type": "text",
  "content": "Welcome to your interview..."
}
```

**Audio Response:**
```json
{
  "type": "audio",
  "audio": "<base64_encoded_audio_data>"
}
```

**State Update:**
```json
{
  "type": "state",
  "phase": "interview",
  "interview_type": "design"
}
```

## Session State Schema

```python
session.state = {
    "interview_phase": "routing" | "intro" | "interview" | "closing" | "done",
    "interview_type": "coding" | "design",
    "candidate_name": str,
    "candidate_role": str,
    "candidate_company": str,
    "start_time": timestamp,
    "conversation_history": [...]
}
```

## Configuration

### Environment Variables

**Required:**
- `GOOGLE_API_KEY`: Google API key for Gemini models

**Optional:**
- `AGENT_MODEL`: Model to use (default: `gemini-2.0-flash-exp`)
- `REMOTE_AGENT_URLS`: Comma-separated A2A agent URLs
- `LOG_LEVEL`: Logging level (default: `INFO`)

### Remote Agent URLs

```env
REMOTE_AGENT_URLS=http://localhost:8001,http://localhost:8002,http://localhost:8003,http://localhost:8004
```

The orchestrator will auto-discover agent cards at:
```
<url>/.well-known/agent-card.json
```

## Streaming Configuration

**Mode:** `StreamingMode.BIDI` (bidirectional)
**Features:**
- Real-time user interruption support
- Streaming text and audio responses
- Turn-based conversation management

## Model Configuration

**Default Model:** `gemini-2.0-flash-exp`
**Supported Models:**
- `gemini-2.0-flash-exp` (recommended for real-time)
- `gemini-1.5-pro` (higher quality)
- `gemini-1.5-flash` (faster)

**Model Selection per Agent:**
All sub-agents inherit the root agent's model configuration, but can be overridden individually.

## Error Handling

### Connection Errors
- WebSocket disconnection: Clean up session and resources
- Timeout: Send keepalive messages every 30s

### Agent Errors
- Agent failure: Log error, notify user, attempt graceful degradation
- Remote agent unavailable: Continue without specialized skills

### Validation Errors
- Invalid message format: Return error message to client
- Missing required fields: Prompt user for missing information

## Performance Characteristics

**Latency:**
- Text mode: <1s typical response time
- Audio mode: <2s typical response time (includes TTS/STT)

**Throughput:**
- Supports 100+ concurrent sessions
- Limited by Gemini API rate limits

**Session Limits:**
- Max session duration: 2 hours
- Max messages per session: 1000

## Use Cases

### 1. Coding Interview
```
routing → intro → coding_agent → closing → done
```

**Flow:**
1. Routing determines "coding" type
2. Intro greets candidate
3. Coding agent asks programming problems
4. Closing wraps up

### 2. System Design Interview
```
routing → intro → design_agent → closing → done
         (may use remote agents)
```

**Flow:**
1. Routing determines "design" type
2. Intro greets candidate
3. Design agent asks system design questions
4. Design agent uses remote agents (Google, Meta, etc.) for specialized evaluation
5. Closing wraps up

## Integration with Remote Agents

### Auto-Discovery

```python
from interview_orchestrator.shared.infra.a2a.agent_registry import AgentProviderRegistry

# Agents are configured via environment variables
# See INTERVIEW_AGENTS, GOOGLE_AGENT_URL, etc.
options = AgentProviderRegistry.get_available_options()
# Returns: {"google": ["coding", "system_design"], "meta": ["system_design"]}
```

### Skill Delegation

Design agent automatically delegates to appropriate remote agents based on topic:
- **Scale calculations** → google_agent.analyze_scale_requirements
- **Social graph design** → meta_agent.design_social_graph
- **AWS architecture** → amazon_agent.suggest_aws_services
- **Ride-sharing metrics** → uber_agent.calculate_trip_metrics

## Monitoring and Observability

### Logging

```python
import logging
logger = logging.getLogger("interview_orchestrator")
```

**Log Levels:**
- `DEBUG`: Detailed agent interactions
- `INFO`: Phase transitions, agent transfers
- `WARNING`: Degraded performance, missing agents
- `ERROR`: Agent failures, connection errors

### Metrics

Track:
- Session duration by interview type
- Message count per session
- Agent transfer frequency
- Remote agent usage statistics

## Security Considerations

**Authentication:** Not implemented (add as needed)
**Rate Limiting:** Subject to Gemini API limits
**Input Validation:** All messages validated before processing
**Session Isolation:** Each WebSocket connection has isolated session

## Development Workflow

### Local Testing

1. Start remote agents (optional):
   ```bash
   # Terminal 1: Google Agent
   cd services/google-agent && uvicorn agent:a2a_app --port 8003

   # Terminal 2: Meta Agent
   cd services/meta-agent && uvicorn agent:a2a_app --port 8004
   ```

2. Start orchestrator:
   ```bash
   cd services/interview-orchestrator
   python -m uvicorn interview_orchestrator.server:app --port 8000 --reload
   ```

3. Connect client:
   ```javascript
   const ws = new WebSocket('ws://localhost:8000/ws');
   ws.send(JSON.stringify({type: 'message', content: 'Hello'}));
   ```

### Testing Without Remote Agents

The orchestrator gracefully degrades if remote agents are unavailable. The design agent will conduct interviews without specialized skill delegation.
