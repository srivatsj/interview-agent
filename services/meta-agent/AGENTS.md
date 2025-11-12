# Meta Agent - LLM Documentation

## Agent Specification

**Name:** `meta_system_design_agent`
**Type:** A2A Remote Agent
**Port:** 8004
**Protocol:** A2A (Agent-to-Agent)
**Agent Card:** `http://localhost:8004/.well-known/agent-card.json`

## Capabilities

This agent specializes in Meta-style system design interviews focusing on:
- Social graph architecture (connections, feeds, followers)
- Performance optimization for high-traffic systems
- Caching strategies and database optimizations
- Real-time systems and latency reduction

## Skills

### Skill 1: design_social_graph

**ID:** `design_social_graph`
**Function:** `design_social_graph(scenario: str) -> dict`
**Tags:** `["social-graph", "feeds", "connections"]`

**Purpose:**
Designs social graph architecture for friend connections, news feeds, and follower systems. Provides recommendations for graph storage, feed generation, and performance optimization.

**Input Parameters:**
- `scenario` (string, required): Description of the social graph scenario
  - Example: "3 billion users with average 500 friends each"
  - Example: "News feed for 2B users with 1000 posts/day"
  - Example: "Instagram-like follower system with asymmetric relationships"

**Output Schema:**
```json
{
  "success": true,
  "skill": "design_social_graph",
  "scenario": "<input scenario>",
  "design": {
    "graph_storage": {
      "adjacency_list": "<storage approach>",
      "graph_db": "<graph database recommendation>",
      "sharding": "<sharding strategy>"
    },
    "news_feed": {
      "ranking": "<ranking algorithm>",
      "caching": "<caching strategy>",
      "fan_out": "<fan-out approach>"
    },
    "performance": {
      "qps": "<expected QPS>",
      "latency": "<latency target>",
      "recommendation": "<optimization recommendations>"
    }
  },
  "message": "Social graph design for: <scenario>"
}
```

**When to Use:**
- Candidate discusses social networks or connections
- Need to design friend/follower relationships
- Evaluating news feed generation strategies
- Planning graph data storage and retrieval

### Skill 2: optimize_performance

**ID:** `optimize_performance`
**Function:** `optimize_performance(requirement: str) -> dict`
**Tags:** `["performance", "optimization", "latency"]`

**Purpose:**
Suggests performance optimization strategies including caching, database optimizations, architectural patterns, and monitoring approaches.

**Input Parameters:**
- `requirement` (string, required): Description of the performance requirement
  - Example: "reduce API latency from 500ms to 100ms"
  - Example: "handle 10x traffic spike during peak hours"
  - Example: "optimize database queries for user timeline"

**Output Schema:**
```json
{
  "success": true,
  "skill": "optimize_performance",
  "requirement": "<input requirement>",
  "strategies": {
    "caching": ["<caching strategy 1>", "<caching strategy 2>", ...],
    "database": ["<db optimization 1>", "<db optimization 2>", ...],
    "architecture": ["<architectural pattern 1>", "<architectural pattern 2>", ...],
    "monitoring": ["<monitoring approach 1>", "<monitoring approach 2>", ...]
  },
  "message": "Performance optimization for: <requirement>"
}
```

**When to Use:**
- Candidate discusses performance requirements
- Need latency reduction strategies
- Evaluating throughput optimization
- Planning caching layers or database optimizations
- Discussing monitoring and observability

## Integration

### As RemoteA2aAgent

```python
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent, AGENT_CARD_WELL_KNOWN_PATH

meta_agent = RemoteA2aAgent(
    name="meta_agent",
    description="Meta system design expert for social graphs and performance optimization",
    agent_card="http://localhost:8004/.well-known/agent-card.json"
)
```

### Direct Function Call

```python
# Via agent's tools
result = design_social_graph("2B users, 500 friends avg, news feed generation")
result = optimize_performance("reduce feed load time to <100ms P99")
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

1. **Social Graph Design Phase:**
   - Use `design_social_graph` when candidate discusses social features
   - Evaluate graph storage and retrieval strategies
   - Assess news feed generation approaches

2. **Performance Optimization Phase:**
   - Use `optimize_performance` when discussing latency/throughput
   - Validate caching strategies
   - Evaluate database and architectural optimizations

## Example Invocations

**Scenario 1: Facebook-like Social Network**
```python
result = design_social_graph(
    "3 billion users, average 500 friends, news feed with 100 posts per load"
)
# Returns graph storage, feed generation, and performance recommendations
```

**Scenario 2: API Latency Optimization**
```python
result = optimize_performance(
    "User timeline API currently at 800ms, need to reduce to <200ms P99"
)
# Returns caching, database, architecture, and monitoring strategies
```

## Agent Card Structure

```json
{
  "name": "meta_system_design_agent",
  "url": "http://localhost:8004",
  "description": "Meta system design interview expert for social graphs and performance optimization",
  "version": "1.0.0",
  "skills": [
    {
      "id": "design_social_graph",
      "name": "Design Social Graph",
      "description": "Designs social graph architecture for friend connections, news feeds, and follower systems",
      "tags": ["social-graph", "feeds", "connections"]
    },
    {
      "id": "optimize_performance",
      "name": "Optimize Performance",
      "description": "Suggests performance optimization strategies for latency, throughput, and resource efficiency",
      "tags": ["performance", "optimization", "latency"]
    }
  ],
  "defaultInputModes": ["text/plain"],
  "defaultOutputModes": ["text/plain"]
}
```

## Common Integration Patterns

### With Interview Orchestrator

```python
# In system design interview agent
from google.adk.agents.remote_a2a_agent import RemoteA2aAgent

meta_agent = RemoteA2aAgent(
    name="meta_expert",
    description="Meta system design expert",
    agent_card="http://localhost:8004/.well-known/agent-card.json"
)

design_agent = Agent(
    name="design_interviewer",
    sub_agents=[meta_agent],
    instruction="""When candidate discusses:
    - Social networks, feeds, or connections -> use meta_expert.design_social_graph
    - Performance optimization or latency -> use meta_expert.optimize_performance
    """
)
```
