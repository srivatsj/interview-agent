# ADK Deployment & Best Practices

## Development Workflow

### Project Structure
```
my_agent_project/
├── agent_module/
│   ├── __init__.py
│   ├── agent.py           # Main agent definition (root_agent)
│   ├── tools.py           # Custom tool functions
│   └── custom_agents.py   # Sub-agent definitions
├── .env                   # API keys and config
├── requirements.txt
└── README.md
```

### Environment Setup

**Virtual Environment:**
```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
.venv\Scripts\activate     # Windows
```

**Install ADK:**
```bash
pip install google-adk
```

**Environment Variables (.env):**
```bash
# Google AI Studio
GOOGLE_API_KEY=your-api-key

# OR Vertex AI
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
```

### Agent Module Requirements

**Root Agent Naming:**
The main agent must be named `root_agent` for ADK CLI tools to discover it:

```python
# agent.py
from google.adk.agents import Agent

root_agent = Agent(  # MUST be named 'root_agent'
    name='my_agent',
    model='gemini-2.5-flash',
    # ... other config
)
```

**Module Exports:**
```python
# __init__.py
from .agent import root_agent

__all__ = ['root_agent']
```

## Deployment Options

### Local Development
**Dev UI:**
```bash
cd parent_folder  # Navigate to parent of agent folder
adk web
# Access at http://localhost:8000
```

**CLI:**
```bash
adk run agent_module.root_agent "Your query here"
```

**API Server:**
```bash
adk api_server
# Exposes POST /run endpoint at http://localhost:8080
```

### Cloud Deployment

#### Cloud Run (Docker)
1. **Create Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080
CMD ["adk", "api_server", "--host", "0.0.0.0", "--port", "8080"]
```

2. **Deploy:**
```bash
gcloud run deploy my-agent \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated
```

#### Vertex AI Agent Engine
Production-grade managed service with auto-scaling and session persistence:

```python
# Deploy agent to Vertex AI
from google.cloud import aiplatform

aiplatform.init(project="your-project", location="us-central1")

# Deploy using Reasoning Engine
reasoning_engine = aiplatform.ReasoningEngine.create(
    reasoning_engine_source="agent_module",
    requirements=["google-adk"],
    display_name="my-agent"
)
```

## Best Practices

### Agent Design

#### Clear Instructions
- Be specific about agent's role and capabilities
- Reference tools by name in instructions
- Provide examples of expected behavior
- Use imperative tone ("Use tool X when...", "Analyze Y by...")

**Good:**
```python
instruction="""You are a weather assistant. When users ask about weather:
1. Use get_weather tool to fetch current conditions
2. Use forecast_weather tool for future predictions
3. Always include temperature and conditions in your response"""
```

**Bad:**
```python
instruction="Help with weather"  # Too vague
```

#### Tool Documentation
The docstring is your tool's interface to the LLM:

**Excellent Docstring:**
```python
def search_database(query: str, max_results: int = 10) -> dict:
    """
    Search the company knowledge base for relevant information.
    
    Use this tool when users ask about:
    - Company policies, procedures, or guidelines
    - Product documentation or specifications
    - Historical project information
    
    Args:
        query: Natural language search query (e.g., "vacation policy" or "product specs for Model X")
        max_results: Maximum number of results to return (default: 10, range: 1-50)
    
    Returns:
        dict with keys:
        - results: List of matching documents with title, snippet, and relevance score
        - total_count: Total number of matches found
        - search_time_ms: Query execution time
    """
    # Implementation
```

#### State Management
- Use `output_key` for agent-to-agent communication
- Leverage `temp:` prefix for turn-specific state
- Clean up state when no longer needed
- Document state keys used by your agents

```python
# Producer agent
producer = LlmAgent(
    name="DataFetcher",
    output_key="fetched_data",  # Writes to state['fetched_data']
    instruction="Fetch data from API"
)

# Consumer agent
consumer = LlmAgent(
    name="DataAnalyzer",
    instruction="Analyze the data: {fetched_data}",  # Reads from state
)
```

#### Error Handling in Tools
Return structured errors that help the agent recover:

```python
def call_api(endpoint: str) -> dict:
    """Call external API endpoint"""
    try:
        response = requests.get(f"https://api.example.com/{endpoint}")
        response.raise_for_status()
        return {"success": True, "data": response.json()}
    except requests.HTTPError as e:
        return {
            "success": False,
            "error": f"API returned {e.response.status_code}",
            "suggestion": "Try a different endpoint or check API status"
        }
    except requests.RequestException as e:
        return {
            "success": False,
            "error": "Network connection failed",
            "suggestion": "Check internet connectivity and retry"
        }
```

### Multi-Agent Systems

#### Agent Specialization
Create focused agents for specific tasks:

```python
# GOOD: Specialized agents
greeter = LlmAgent(
    name="Greeter",
    description="Handles greetings and introductions",
    instruction="Greet users warmly and introduce yourself"
)

task_executor = LlmAgent(
    name="TaskExecutor", 
    description="Executes user-requested tasks",
    instruction="Execute the user's task using available tools"
)

# BAD: One agent doing everything
do_everything = LlmAgent(
    name="DoEverything",
    description="Does greetings, tasks, farewells, and more",
    instruction="Handle all user requests"  # Too broad!
)
```

#### Delegation vs Workflow
Choose the right orchestration pattern:

**Use LLM-Driven Delegation when:**
- Agent needs to dynamically decide which specialist to use
- Request routing requires understanding context/intent
- Multiple specialists could handle overlapping queries

**Use Workflow Agents when:**
- Process has fixed, predictable steps
- Order of execution is always the same
- No dynamic routing needed

```python
# Dynamic routing with LLM delegation
coordinator = LlmAgent(
    name="Coordinator",
    description="Routes requests intelligently",
    sub_agents=[specialist1, specialist2, specialist3],
    instruction="Analyze request and transfer to appropriate specialist"
)

# Fixed pipeline with workflow agent
pipeline = SequentialAgent(
    name="Pipeline",
    sub_agents=[step1, step2, step3]  # Always runs in order
)
```

### Performance Optimization

#### Parallel Execution
Use ParallelAgent for independent operations:

```python
# Fetch from multiple sources simultaneously
parallel_fetch = ParallelAgent(
    name="ParallelFetch",
    sub_agents=[
        LlmAgent(name="FetchAPI1", output_key="api1_data"),
        LlmAgent(name="FetchAPI2", output_key="api2_data"),
        LlmAgent(name="FetchAPI3", output_key="api3_data")
    ]
)
```

#### Model Selection
Choose appropriate models for each task:

- **gemini-2.5-flash:** Complex reasoning, planning, multi-step tasks
- **gemini-2.0-flash:** Fast responses, simple queries, high-throughput scenarios
- **gemini-2.0-flash-thinking:** Deep analysis requiring extended reasoning

```python
# Use faster model for simple greeter
greeter = Agent(model='gemini-2.0-flash', ...)

# Use advanced model for complex coordinator  
coordinator = Agent(model='gemini-2.5-flash', ...)
```

#### Streaming
Enable streaming for real-time user feedback:

```python
async for event in runner.run(agent=root_agent, query=query):
    if event.type == "model_response":
        print(event.data.text, end="", flush=True)
```

### Testing & Debugging

#### Logging
Enable comprehensive logging:

```python
import logging
logging.basicConfig(level=logging.INFO)

# ADK will log:
# - Agent invocations
# - Tool calls
# - State changes
# - Model responses
```

#### Dev UI Features
- **Events Tab:** Inspect function calls, model responses, and state changes
- **Trace Button:** View latency and execution timeline
- **State Inspector:** Monitor session state throughout conversation

#### Evaluation
Use ADK's built-in evaluation system:

```bash
# Create evaluation dataset
adk eval create my_agent my_eval_set.json

# Run evaluation
adk eval run my_agent my_eval_set.json

# View results in Dev UI
adk web
```

### Security Best Practices

#### API Key Management
- Never commit keys to version control
- Use environment variables or secret management services
- Rotate keys regularly
- Use separate keys for dev/staging/prod

#### Tool Safety
- Validate all tool inputs
- Sanitize user-provided data before external API calls
- Implement rate limiting for expensive operations
- Use LongRunningFunctionTool for sensitive actions requiring approval

#### State Hygiene
- Don't store sensitive data (passwords, tokens) in state
- Clear sensitive data after use
- Use `temp:` prefix for ephemeral sensitive data
- Implement state encryption for production deployments

### Common Pitfalls

#### Avoid These Mistakes

**1. Missing docstrings:**
```python
# BAD: LLM won't understand when/how to use this
def my_tool(x: str) -> dict:
    return {"result": x.upper()}

# GOOD: Clear documentation
def my_tool(text: str) -> dict:
    """Converts text to uppercase. Use when user requests text transformation."""
    return {"result": text.upper()}
```

**2. Vague agent descriptions:**
```python
# BAD: Coordinator won't know when to delegate
specialist = LlmAgent(name="Helper", description="Helps with stuff")

# GOOD: Specific capabilities
specialist = LlmAgent(
    name="DataAnalyzer",
    description="Analyzes numerical data, generates statistics, creates visualizations"
)
```

**3. Forgetting output_key:**
```python
# BAD: Next agent can't access results
agent_a = LlmAgent(name="Fetcher", ...)

# GOOD: Results stored in state
agent_a = LlmAgent(name="Fetcher", output_key="fetched_data")
```

**4. State key typos:**
```python
# BAD: Typo in instruction won't match state key
agent_a = LlmAgent(output_key="user_data")
agent_b = LlmAgent(instruction="Process {userdata}")  # Typo!

# GOOD: Consistent naming
agent_a = LlmAgent(output_key="user_data")
agent_b = LlmAgent(instruction="Process {user_data}")
```

**5. Ignoring state persistence:**
```python
# State changes only persist after yielding an event
context.state['key'] = 'value'  # Not persisted yet!
# Must continue agent execution to yield event for persistence
```

## A2A Protocol (Agent-to-Agent)

### Overview
A2A is an open standard for agent interoperability, allowing ADK agents to communicate with agents from other frameworks (LangGraph, CrewAI, etc.).

### Implementing A2A

**1. Expose agent metadata:**
```python
# Create .well-known/agent.json
{
  "id": "my-agent",
  "name": "My ADK Agent",
  "description": "Handles data processing tasks",
  "skills": [
    {
      "name": "data_analysis",
      "description": "Analyzes structured data and generates insights"
    }
  ],
  "endpoint": "https://my-agent.example.com/run"
}
```

**2. Standard /run endpoint:**
ADK's api_server automatically exposes this:
```bash
adk api_server  # Exposes POST /run at http://localhost:8080/run
```

**3. Calling external A2A agents:**
```python
# Use as a tool in your ADK agent
import httpx

async def call_external_agent(query: str) -> dict:
    """Call external A2A-compliant agent"""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://external-agent.example.com/run",
            json={"query": query}
        )
        return response.json()

root_agent = Agent(
    tools=[call_external_agent]
)
```

### Security Note
Always treat external agents as untrusted:
- Validate all responses
- Sanitize agent-provided data before using in prompts
- Implement authentication/authorization
- Rate limit external agent calls
