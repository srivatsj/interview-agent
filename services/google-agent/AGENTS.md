# Google Agent - LLM Documentation

## Agent Specification

**Name:** `google_system_design_agent`
**Type:** A2A Remote Agent
**Port:** 8003
**Protocol:** A2A (Agent-to-Agent)
**Agent Card:** `http://localhost:8003/.well-known/agent-card.json`

## Capabilities

This agent specializes in Google-style system design interviews focusing on:
- Massive-scale system analysis (billions of users)
- Distributed systems architecture patterns
- Infrastructure capacity planning
- Consistency and replication strategies

## Skills

### Skill 1: analyze_scale_requirements

**ID:** `analyze_scale_requirements`
**Function:** `analyze_scale_requirements(scenario: str) -> dict`
**Tags:** `["scale", "billions", "infrastructure"]`

**Purpose:**
Analyzes scale requirements for systems handling billions of users. Provides calculations for throughput, storage, bandwidth, and infrastructure needs.

**Input Parameters:**
- `scenario` (string, required): Description of the scale scenario
  - Example: "2 billion users, 50 searches per day per user"
  - Example: "Global video streaming platform with 1B daily active users"

**Output Schema:**
```json
{
  "success": true,
  "skill": "analyze_scale_requirements",
  "scenario": "<input scenario>",
  "analysis": {
    "requests_per_second": "<QPS calculation>",
    "storage_per_day": "<storage estimate>",
    "bandwidth": "<bandwidth requirement>",
    "infrastructure": {
      "data_centers": "<number and distribution>",
      "servers": "<server count estimate>",
      "recommendation": "<optimization recommendations>"
    }
  },
  "message": "Scale analysis for: <scenario>"
}
```

**When to Use:**
- Candidate discusses user scale (millions/billions)
- Need to calculate QPS, storage, or bandwidth
- Evaluating infrastructure requirements
- Planning data center distribution

### Skill 2: design_distributed_systems

**ID:** `design_distributed_systems`
**Function:** `design_distributed_systems(use_case: str) -> dict`
**Tags:** `["distributed", "consistency", "replication"]`

**Purpose:**
Suggests distributed system architecture patterns including consistency models, replication strategies, sharding approaches, and design patterns.

**Input Parameters:**
- `use_case` (string, required): Description of the distributed system requirement
  - Example: "global state management across regions"
  - Example: "distributed transaction handling"
  - Example: "eventual consistency for user profiles"

**Output Schema:**
```json
{
  "success": true,
  "skill": "design_distributed_systems",
  "use_case": "<input use case>",
  "suggestions": {
    "consistency": ["<consistency model 1>", "<consistency model 2>", ...],
    "replication": ["<replication strategy 1>", "<replication strategy 2>", ...],
    "sharding": ["<sharding approach 1>", "<sharding approach 2>", ...],
    "patterns": ["<design pattern 1>", "<design pattern 2>", ...]
  },
  "message": "Distributed system design for: <use_case>"
}
```

**When to Use:**
- Candidate discusses distributed systems architecture
- Need consistency model recommendations (strong, eventual, causal)
- Evaluating replication strategies (multi-region, leader-follower)
- Planning data partitioning or sharding
- Discussing design patterns (CQRS, event sourcing, saga)

## Integration

### As RemoteA2aAgent

```python
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH

google_agent = RemoteA2aAgent(
    name="google_agent",
    description="Google system design expert for massive scale and distributed systems",
    agent_card="http://localhost:8003/.well-known/agent-card.json"
)
```

### Direct Function Call

```python
# Via agent's tools
result = analyze_scale_requirements("5 billion users, 100 requests/day/user")
result = design_distributed_systems("global distributed database")
```

## Model Configuration

**Default Model:** `gemini-2.0-flash-exp`
**Configurable via:** `AGENT_MODEL` environment variable

**Supported Models:**
- `gemini-2.0-flash-exp` (default, fastest)
- `gemini-1.5-pro`
- `gemini-1.5-flash`

## State Management

**Stateless:** Each skill call is independent
**Session:** Not required
**Context:** Agent does not maintain conversation history

## Error Handling

All skills return:
- `success: true` on successful execution
- `success: false` with error details on failure

## Performance Characteristics

**Latency:** <500ms typical response time
**Throughput:** Supports concurrent requests
**Rate Limits:** Subject to Gemini API limits

## Use Cases in Interview Context

1. **Scale Calculation Phase:**
   - Use `analyze_scale_requirements` when candidate proposes system scale
   - Verify candidate's QPS and storage calculations
   - Evaluate infrastructure planning

2. **Architecture Design Phase:**
   - Use `design_distributed_systems` when discussing consistency requirements
   - Validate replication and sharding strategies
   - Assess distributed patterns knowledge

## Example Invocations

**Scenario 1: Global Search Engine**
```python
result = analyze_scale_requirements(
    "3 billion users, 20 searches per day per user, 10KB average result size"
)
# Returns QPS, storage, bandwidth calculations
```

**Scenario 2: Distributed Database**
```python
result = design_distributed_systems(
    "Multi-region database requiring strong consistency for financial transactions"
)
# Returns consistency models, replication strategies, sharding approaches
```

## Agent Card Structure

```json
{
  "name": "google_system_design_agent",
  "url": "http://localhost:8003",
  "description": "Google system design interview expert for massive scale and distributed systems",
  "version": "1.0.0",
  "skills": [
    {
      "id": "analyze_scale_requirements",
      "name": "Analyze Scale Requirements",
      "description": "Analyzes requirements for billion-user scale systems with QPS, storage, and infrastructure planning",
      "tags": ["scale", "billions", "infrastructure"]
    },
    {
      "id": "design_distributed_systems",
      "name": "Design Distributed Systems",
      "description": "Suggests distributed system patterns including consistency, replication, sharding, and consensus",
      "tags": ["distributed", "consistency", "replication"]
    }
  ],
  "defaultInputModes": ["text/plain"],
  "defaultOutputModes": ["text/plain"]
}
```
