# Interview Agent Architecture

## Single-Agent Pattern with State-Driven Delegation

The interview-orchestrator uses a **single `LlmAgent`** with dynamic instruction that changes based on session state. No manual orchestration or sub-agent delegation needed - ADK handles everything automatically.

```
root_agent (Single LlmAgent)
    │
    ├── get_dynamic_instruction(ctx)  # Returns phase-specific instruction
    │   ├── routing phase  → routing_agent.txt
    │   ├── intro phase    → intro_agent.txt
    │   ├── design phase   → design_phase.txt
    │   └── closing phase  → closing_agent.txt
    │
    └── Tools (trigger state transitions)
        ├── set_routing_decision      → transitions to intro
        ├── save_candidate_info       → transitions to design
        ├── initialize_design_phase   → loads question
        ├── mark_design_complete      → transitions to closing
        └── mark_interview_complete   → transitions to done
```

## How It Works

### Dynamic Instruction

The agent's instruction dynamically changes based on the `interview_phase` state:

```python
def get_dynamic_instruction(ctx: ReadonlyContext) -> str:
    """Generate instruction based on current interview phase."""
    phase = ctx.session.state.get("interview_phase", "routing")

    if phase == "routing":
        return load_prompt("routing_agent.txt", ...)
    elif phase == "intro":
        return load_prompt("intro_agent.txt", ...)
    elif phase == "design":
        return load_prompt("design_phase.txt", ...)
    elif phase == "closing":
        return load_prompt("closing_agent.txt", ...)
    else:
        return "Interview is complete."
```

**Key Insight:** When a tool updates `interview_phase` in state, ADK automatically re-evaluates the instruction and adapts the agent's behavior. No manual delegation needed!

### Phase Transitions via Tools

Each phase has tools that update state to trigger transitions:

#### 1. Routing Phase → Intro Phase
```python
def set_routing_decision(company: str, interview_type: str, tool_context: ToolContext):
    """Save routing decision and transition to intro phase."""
    tool_context.state["routing_decision"] = {
        "company": company.lower(),
        "interview_type": interview_type.lower(),
        "confidence": 1.0
    }
    tool_context.state["interview_phase"] = "intro"  # ✅ Triggers re-evaluation
    return f"Routing to {company} {interview_type}. Starting intro phase."
```

#### 2. Intro Phase → Design Phase
```python
def save_candidate_info(name, years_experience, domain, projects, tool_context: ToolContext):
    """Save candidate info and transition to design phase."""
    tool_context.state["candidate_info"] = {
        "name": name,
        "years_experience": years_experience,
        "domain": domain,
        "projects": projects
    }
    tool_context.state["interview_phase"] = "design"  # ✅ Triggers re-evaluation
    return f"Candidate info saved. Moving to design phase."
```

#### 3. Design Phase Initialization
```python
async def initialize_design_phase(tool_context: ToolContext):
    """Load interview question from company-specific provider."""
    routing = tool_context.state.get("routing_decision", {})
    company = routing.get("company", "default")

    # Get provider (remote A2A or local)
    provider = CompanyFactory.get_tools(company, "system_design")

    # Fetch question
    question = await provider.get_question()
    tool_context.state["interview_question"] = question

    return f"Design phase initialized. Question: {question[:100]}..."
```

#### 4. Design Phase → Closing Phase
```python
def mark_design_complete(tool_context: ToolContext):
    """Mark design phase complete and transition to closing."""
    tool_context.state["design_complete"] = True
    tool_context.state["interview_phase"] = "closing"  # ✅ Triggers re-evaluation
    return "Design phase complete. Moving to closing remarks."
```

#### 5. Closing Phase → Done
```python
def mark_interview_complete(tool_context: ToolContext):
    """Mark interview complete."""
    tool_context.state["interview_complete"] = True
    tool_context.state["interview_phase"] = "done"  # ✅ Triggers re-evaluation
    return "Interview complete. Thank you!"
```

## State Management

Session state tracks the interview progression:

| State Key | Type | Description |
|-----------|------|-------------|
| `interview_phase` | `"routing" \| "intro" \| "design" \| "closing" \| "done"` | Current phase - drives dynamic instruction |
| `routing_decision` | `{ company, interview_type, confidence }` | Routing choice |
| `candidate_info` | `{ name, years_experience, domain, projects }` | Candidate background |
| `interview_question` | `str` | System design question |
| `design_complete` | `bool` | Design phase finished |
| `interview_complete` | `bool` | Interview finished |

## Company-Specific Design Providers

The design phase uses company-specific providers via the `CompanyFactory`:

### Remote Providers (A2A Protocol)
- **Google Agent**: `http://localhost:10123` (system_design, coding)
- **Meta Agent**: `http://localhost:10125` (system_design)

Remote providers use the A2A (Agent-to-Agent) protocol to delegate design questions to specialized external agents.

### Local Provider (Free Tier)
- **Default Tools**: Built-in system design questions

Falls back to local implementation when no remote agent is configured.

### Provider Selection
```python
# CompanyFactory.get_tools(company, interview_type) returns:
# - RemoteAgentProvider if agent URL configured
# - LocalAgentProvider wrapping default tools otherwise

provider = CompanyFactory.get_tools("google", "system_design")
# → RemoteAgentProvider(agent_url="http://localhost:10123")

provider = CompanyFactory.get_tools("default", "system_design")
# → LocalAgentProvider(DefaultSystemDesignTools())
```

## Benefits of Single-Agent Pattern

1. **No Manual Orchestration**: No custom `run_live()` or `aclosing()` patterns
2. **Persistent Connection**: Single WebSocket throughout all phases
3. **Automatic Delegation**: ADK re-evaluates instruction when state changes
4. **Proper Interruptions**: ADK handles `event.interrupted` correctly
5. **Simpler Code**: Tool-based transitions instead of manual flow control
6. **Easier Testing**: Test instruction logic and tools independently

## Project Structure

```
interview_orchestrator/
├── root_agent.py                         # Single LlmAgent with dynamic instruction
│   ├── get_dynamic_instruction()         # Phase-based instruction selection
│   └── root_agent (LlmAgent instance)    # Uses Live API model
│
├── shared/
│   ├── tools/                            # Phase transition tools
│   │   ├── routing_tools.py              # set_routing_decision
│   │   ├── intro_tools.py                # save_candidate_info
│   │   └── closing_tools.py              # mark_interview_complete
│   │
│   ├── prompts/                          # Phase-specific prompts
│   │   ├── routing_agent.txt
│   │   ├── intro_agent.txt
│   │   ├── design_phase.txt
│   │   └── closing_agent.txt
│   │
│   ├── agent_providers/                  # Design phase providers
│   │   ├── protocol.py                   # InterviewAgentProtocol
│   │   ├── registry.py                   # AgentProviderRegistry
│   │   ├── remote_provider.py            # RemoteAgentProvider (A2A)
│   │   └── local_provider.py             # LocalAgentProvider (wrapper)
│   │
│   ├── factories/
│   │   └── company_factory.py            # Routes to remote/local providers
│   │
│   └── schemas/                          # Data models
│       ├── routing_decision.py
│       └── candidate_info.py
│
└── interview_types/
    └── system_design/
        ├── design_agent_tool.py          # initialize_design_phase, mark_design_complete
        └── tools/
            └── default_tools.py          # Free tier questions
```

## Testing

### Unit Tests
Test tools and instruction logic independently:

```bash
pytest tests/shared/tools/              # Tool tests
pytest tests/interview_types/           # Design tool tests
```

### Integration Tests
Test complete state-driven flow using text messages:

```bash
pytest tests/integration/test_single_agent_flow.py -v
```

## Live API & Bidirectional Streaming

The agent uses Gemini's Live API for real-time audio/video interviews:

- **Model**: `gemini-2.5-flash-native-audio-preview-09-2025`
- **Streaming**: Bidirectional (user can interrupt AI mid-speech)
- **Protocol**: WebSocket via ADK's `run_live()`

Enable bidirectional streaming with:
```python
from google.genai.types import RunConfig, StreamingMode

run_config = RunConfig(streaming_mode=StreamingMode.BIDI)
runner.run_live(..., run_config=run_config)
```

This enables proper user interruption handling where the AI stops speaking when interrupted.

---

**Built with [Google ADK](https://github.com/google/adk) - Agent Development Kit**
