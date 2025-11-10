# ADK Core Concepts Reference

## Agent Types

### LlmAgent (Agent)
The primary agent type powered by Large Language Models for dynamic reasoning, tool selection, and response generation.

**Key Parameters:**
- `name` (required): Unique identifier for the agent
- `model` (required): Model name (e.g., 'gemini-2.5-flash', 'gemini-2.0-flash')
- `description`: Explains the agent's purpose (critical for LLM-driven delegation)
- `instruction`: System prompt guiding agent behavior and tool usage
- `tools`: List of tools the agent can use (FunctionTool, AgentTool, built-in tools)
- `sub_agents`: List of child agents in the hierarchy
- `output_key`: Stores agent response in session state (e.g., `state['key_name']`)
- `input_schema`: Define expected input structure (JSON schema)
- `output_schema`: Define required output structure (JSON schema)

**Best Practices:**
- Use clear, specific instructions that reference tools by name
- Leverage `{variable}` syntax in instructions to inject session state values
- Provide detailed tool descriptions via docstrings
- Use `output_key` to pass results between agents in workflows

### Workflow Agents

#### SequentialAgent
Executes sub-agents one after another in strict order. Deterministic flow control without LLM reasoning.

**Use Cases:**
- Code pipelines (write → review → refactor)
- Data processing workflows (validate → process → report)
- Multi-stage analysis (gather → analyze → synthesize)

**Key Parameters:**
- `name`: Agent identifier
- `sub_agents`: Ordered list of agents to execute sequentially
- `description`: What the pipeline accomplishes

**Communication:** Sub-agents share session state via `output_key` and state variable injection.

#### ParallelAgent
Executes multiple sub-agents concurrently. Returns when all sub-agents complete.

**Use Cases:**
- Multi-source data gathering (fetch from API1, API2, API3 simultaneously)
- Independent research tasks
- Parallel processing of separate data chunks

**Key Parameters:**
- `name`: Agent identifier  
- `sub_agents`: List of agents to execute in parallel
- `description`: What the parallel execution accomplishes

**Note:** Sub-agents should be independent (no inter-agent dependencies during execution).

#### LoopAgent
Repeatedly executes sub-agents until a termination condition is met.

**Use Cases:**
- Iterative refinement (generate → critique → revise loop)
- Data processing batches
- Retry logic with conditions

**Key Parameters:**
- `name`: Agent identifier
- `sub_agents`: Agents to execute in each loop iteration
- `termination_condition`: Function that returns True when loop should stop
- `max_iterations`: Safety limit to prevent infinite loops

### Custom Agents
Create custom orchestration by inheriting from `BaseAgent` and implementing `_run_async_impl` (Python) or `runAsync` (Java).

**Use Cases:**
- Complex conditional logic beyond standard workflow agents
- Custom state management patterns
- Specialized orchestration requirements

## Multi-Agent Architecture

### Agent Hierarchy
Agents form parent-child relationships via `sub_agents` parameter. Parents coordinate children through:
- **LLM-Driven Delegation:** LLM decides which sub-agent to transfer to (requires clear descriptions)
- **Explicit Invocation:** Use AgentTool to wrap sub-agents as callable tools
- **Workflow Orchestration:** Use SequentialAgent, ParallelAgent, LoopAgent for deterministic control

**Navigation:**
- `agent.parent_agent`: Access parent agent
- `agent.find_agent(name)`: Find descendant by name

### Communication Patterns

#### Shared Session State
Primary mechanism for agent communication. Agents read/write to `context.state`:

```python
# Agent A writes
context.state['result'] = "processed data"

# Agent B reads via instruction templating
instruction="Process the data from {result}"
```

**State Namespaces:**
- Persistent state: `context.state['key']` - survives across conversation turns
- Temporary state: `context.state['temp:key']` - cleared after current turn

#### Output Keys
Agents automatically save responses to state using `output_key`:

```python
agent_a = LlmAgent(
    name="DataFetcher",
    output_key="raw_data"  # Saves response to state['raw_data']
)

agent_b = LlmAgent(
    name="DataProcessor",
    instruction="Analyze {raw_data}"  # Reads from state['raw_data']
)
```

## Tools

### Function Tools
Convert Python functions to agent tools. ADK automatically generates schema from function signature.

**Critical Requirements:**
- **Docstring:** LLM uses this to understand when/how to use the tool (most important!)
- **Type hints:** Required for parameter schema generation
- **Return dict:** Preferred return type for structured responses

**Example:**
```python
def get_weather(city: str, units: str = "celsius") -> dict:
    """
    Get current weather for a city.
    
    Use this when the user asks about weather conditions.
    
    Args:
        city: Name of the city
        units: Temperature units (celsius or fahrenheit)
    """
    return {"temperature": 22, "condition": "sunny", "city": city}

agent = Agent(
    tools=[FunctionTool(get_weather)]  # Wrap in FunctionTool
)
```

**Or let ADK auto-wrap:**
```python
agent = Agent(
    tools=[get_weather]  # ADK wraps automatically
)
```

### Agent Tools
Use other agents as tools for delegation:

```python
from google.adk.tools import AgentTool

specialist_agent = LlmAgent(name="Specialist", ...)
coordinator = LlmAgent(
    name="Coordinator",
    tools=[AgentTool(specialist_agent)]
)
```

### Built-in Tools
- **GoogleSearchTool:** Web search capability
- **CodeExecutionTool:** Execute code in sandboxed environment
- **GoogleRagEngineTool:** Vertex AI RAG Engine integration

### Long-Running Tools
Use `LongRunningFunctionTool` for operations requiring human approval or extended processing time. Agent execution pauses until the tool returns a result.

### MCP Tools
Integrate Model Context Protocol servers as tools using `MCPToolset`:

```python
from google.adk.tools.mcp import MCPToolset

mcp_toolset = MCPToolset(
    server_config={
        "command": "npx",
        "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/files"]
    },
    tool_filter=["read_file", "list_directory"]  # Optional: expose specific tools
)

agent = Agent(tools=[mcp_toolset])
```

## Session & State Management

### Session
Represents a single conversation thread with unique ID. Contains:
- **History:** All events (model calls, tool executions)
- **State:** Key-value dictionary for agent memory
- **Metadata:** App name, user ID, creation time

### Session Services

#### InMemorySessionService
For development and testing. Data lost on restart.

```python
from google.adk.sessions import InMemorySessionService
session_service = InMemorySessionService()
```

#### VertexAiSessionService  
Production-grade persistence using Vertex AI Agent Engine.

```python
from google.adk.sessions import VertexAiSessionService
session_service = VertexAiSessionService(
    project_id="your-project",
    location="us-central1"
)
```

### State Operations

**Read state:**
```python
value = context.state.get('key', default_value)
user_name = context.state['user_name']
```

**Write state:**
```python
context.state['result'] = "processed"
context.state['temp:current_step'] = "validation"  # Temporary
```

**State in instructions:**
```python
instruction="Hello {user_name}, your balance is {account_balance}"
```

## Execution & Runtime

### Running Agents

**CLI:**
```bash
adk run agent_module.root_agent "Your query here"
```

**Web UI:**
```bash
adk web  # Start dev UI on http://localhost:8000
```

**API Server:**
```bash
adk api_server  # FastAPI server with /run endpoint
```

**Programmatic:**
```python
from google.adk.runners import InMemoryRunner
from google.adk.sessions import InMemorySessionService

runner = InMemoryRunner(session_service=InMemorySessionService())

async for event in runner.run(
    agent=root_agent,
    app_name="my_app",
    user_id="user123",
    query="Process this data"
):
    print(event.type, event.data)
```

### Event Loop
ADK runtime operates on yield-based event streaming:
1. Runner sends query to agent
2. Agent yields events (model calls, tool executions, state changes)
3. Runner processes events and commits state changes
4. Agent resumes after each yield
5. Final response returned when agent completes

**Key Principle:** State changes are only persisted after yielding an event containing the state delta.

## Model Configuration

### Supported Models

**Google Gemini:**
- `gemini-2.5-flash`: Latest, smartest Gemini model
- `gemini-2.0-flash`: Fast and efficient
- `gemini-2.0-flash-thinking-exp`: Enhanced reasoning

**Via LiteLLM (multi-provider):**
```python
agent = Agent(
    model="gpt-4o",  # OpenAI
    model="claude-sonnet-4",  # Anthropic  
    model="llama3.1-70b",  # Open source
)
```

### Authentication

**Google AI Studio:**
```bash
export GOOGLE_API_KEY="your-key"
```

**Vertex AI:**
```bash
export GOOGLE_GENAI_USE_VERTEXAI=TRUE
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_CLOUD_LOCATION="us-central1"
```

## Common Patterns

### Coordinator Pattern
Central agent routes requests to specialists:

```python
coordinator = LlmAgent(
    name="Coordinator",
    description="Routes user requests to appropriate specialist",
    instruction="""Analyze the user's request and delegate to:
    - GreeterAgent: For greetings and farewells
    - TaskAgent: For task execution
    - SupportAgent: For help and support""",
    sub_agents=[greeter, task_agent, support_agent]
)
```

### Pipeline Pattern
Sequential data processing with state passing:

```python
pipeline = SequentialAgent(
    name="DataPipeline",
    sub_agents=[
        LlmAgent(name="Validator", output_key="validation_status"),
        LlmAgent(name="Processor", output_key="result"),
        LlmAgent(name="Reporter")
    ]
)
```

### Fan-Out/Gather Pattern
Parallel execution with aggregation:

```python
workflow = SequentialAgent(
    sub_agents=[
        ParallelAgent(
            sub_agents=[fetch_api1, fetch_api2, fetch_api3]
        ),
        LlmAgent(name="Aggregator", instruction="Combine {api1_data}, {api2_data}, {api3_data}")
    ]
)
```

### Iterative Refinement
Loop-based improvement:

```python
refinement = LoopAgent(
    sub_agents=[
        LlmAgent(name="Generator", output_key="content"),
        LlmAgent(name="Critic", output_key="critique"),
        LlmAgent(name="Reviser", output_key="revised_content")
    ],
    termination_condition=lambda ctx: ctx.state.get('critique') == 'approved',
    max_iterations=5
)
```
