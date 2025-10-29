# Interview Agent Catalog

| Agent | Purpose | Key Features | Requirements |
| ----- | ------- | ------------ | ------------ |
| `RootCustomAgent` | Main orchestrator for multi-phase system design interviews using Google ADK. | Deterministic routing, phase orchestration, tool-backed state, record/replay testing. Company-specific interview flows (Amazon, Google, Meta). | Google API key with Gemini access |

## Agent Hierarchy

### Root Agent
- **RootCustomAgent**: Entrypoint that delegates based on persisted routing decisions

### Interview Types
- **System Design Orchestrator**: Coordinates interview phases (intro → design phases → closing)
- **Phase Agent**: LLM-driven phase management
- **Company-Specific Agents**: Amazon, Google, Meta interview styles

### Shared Agents
- **Intro Agent**: Reusable introduction phase
- **Closing Agent**: Reusable closing phase

## Architecture

The interview agent uses:
- **Deterministic routing** from root agent
- **Phase orchestration** through system-design flows
- **Tool-backed state** with company-specific providers
- **Record/replay testing** for integration coverage

## Project Structure

```
interview_agent/
├── root_agent.py                         # RootCustomAgent entrypoint
├── interview_types/
│   └── system_design/
│       ├── orchestrator.py               # Coordinates interview phases
│       ├── system_design_agent.py        # Company-specific orchestration
│       ├── phase_agent.py                # LLM-driven phase management
│       └── providers/                    # Tool definitions per company
├── shared/
│   ├── agents/                           # Intro/closing reusable agents
│   ├── prompts/                          # External prompt templates
│   ├── schemas/                          # Pydantic data contracts
│   └── constants.py
└── ...
```
