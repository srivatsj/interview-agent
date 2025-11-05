# Interview Agent Architecture

## Agent Hierarchy

```
RootCustomAgent (Routing)
    └── SystemDesignOrchestrator
        ├── IntroAgent (collect candidate info)
        ├── SystemDesignAgent (multi-phase interview)
        │   ├── PhaseAgent (LLM-driven phase management)
        │   └── ToolProvider (local or remote A2A)
        └── ClosingAgent (feedback & next steps)
```

## Key Components

### Root Agent
- **RootCustomAgent**: Routes to appropriate interview based on company + type
- Uses `set_routing_decision` tool to persist routing state

### System Design Orchestrator
- **Phase flow**: intro → design → closing
- **State-based transitions**: Checks for `candidate_info` before moving to design
- **Supports**: Google (remote A2A), Meta (remote A2A), Amazon (local tools)

### Reusable Agents
- **IntroAgent**: Collects candidate background via `save_candidate_info` tool
- **ClosingAgent**: Provides feedback and next steps

### Design Agent
- **PhaseAgent**: LLM-driven multi-turn conversations per phase
- **Tool Providers**:
  - Remote (google, meta): A2A protocol at `localhost:10123`, `localhost:10125`
  - Local (amazon): Legacy local tool implementation

## State Management

Session state tracks:
- `routing_decision` - Company and interview type
- `candidate_info` - Name, experience, domain, projects
- `interview_phase` - Current phase (intro, design, closing, done)
- `current_phase` / `current_phase_idx` - Design phase progression

## Project Structure

```
interview_orchestrator/
├── root_agent.py                         # RootCustomAgent entrypoint
├── interview_types/
│   └── system_design/
│       ├── orchestrator.py               # Coordinates interview phases
│       ├── system_design_agent.py        # Company-specific orchestration
│       ├── phase_agent.py                # LLM-driven phase management
│       └── tools/                        # Tool definitions (local fallbacks)
├── shared/
│   ├── agents/                           # Intro/closing reusable agents
│   ├── agent_providers/                  # Remote A2A and local agent providers
│   ├── factories/                        # Interview and company factory patterns
│   │   ├── interview_factory.py          # Creates interview orchestrators
│   │   └── company_factory.py            # Routes to remote/local agents
│   ├── prompts/                          # External prompt templates
│   ├── schemas/                          # Pydantic data contracts
│   └── constants.py
└── ...
```
