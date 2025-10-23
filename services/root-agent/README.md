# Root Agent - Interview Router

Custom agent built with Google ADK for routing interview practice sessions.

## Setup

### Prerequisites
- Python 3.10+
- [uv](https://github.com/astral-sh/uv)

### Installation

```bash
# Clone and navigate to root-agent directory
cd services/root-agent

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Run tests
pytest

# Run linter
ruff check .

# Format code
ruff format .
```

## Structure

```
root_agent/
├── shared/
│   ├── agents/          # Reusable agents (intro, closing)
│   ├── prompts/         # External prompt templates
│   ├── schemas/         # Pydantic schemas
│   └── constants.py     # Shared constants
├── interview_types/
│   └── system_design/   # System design interview orchestrator
└── root_agent.py        # Custom BaseAgent with deterministic routing
```

## Features

- **Deterministic routing**: Pattern-based company/interview type detection
- **Tool-based state management**: Uses ADK tools for state persistence
- **Custom BaseAgent**: Explicit control flow to reduce LLM calls
- **External prompts**: Prompts stored in text files with constant injection
