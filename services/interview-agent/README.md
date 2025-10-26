# Interview Agent - Interview Router

Custom agent built with Google ADK for routing interview practice sessions.

## Setup

### Prerequisites
- Python 3.10+
- [uv](https://github.com/astral-sh/uv)
- Google API key with Gemini access

### Installation

```bash
# Clone and navigate to interview agent directory
cd services/interview-agent

# Create virtual environment and install dependencies
uv venv
source .venv/bin/activate
uv pip install -e ".[dev]"

# Set up environment variables
# Create a .env file or export directly:
export GOOGLE_API_KEY=your_api_key_here
```

## Running Tests

### Unit Tests

Unit tests use mocks and don't require API calls. They run quickly and test individual components:

```bash
# Run all unit tests
pytest tests/ --ignore=tests/integration/

# Run specific unit test files
pytest tests/test_agent.py -v
pytest tests/shared/agents/test_intro_agent.py -v
pytest tests/interview_types/system_design/test_main_agent.py -v
```

### Integration Tests

Integration tests use real ADK infrastructure (Runner, SessionService) and the **record/replay pattern** for LLM responses:

#### Record Mode (First Run)
Uses real LLM API and saves responses to JSON files:

```bash
# Record LLM responses (makes real API calls)
RECORD_MODE=true pytest tests/integration/test_interview_flow.py -v
```

This will:
- Make real API calls to Gemini
- Save LLM responses to `tests/integration/recordings/`
- Takes ~20-30 seconds
- Costs a few cents in API usage

#### Replay Mode (Subsequent Runs)
Replays saved responses without API calls:

```bash
# Replay saved responses (no API calls, fast)
pytest tests/integration/test_interview_flow.py -v
```

This will:
- Use saved responses from recordings
- No API calls or costs
- Runs in ~4-5 seconds
- Deterministic and repeatable

#### Re-recording After Code Changes

Re-record responses when:
- Agent code changes (prompts, tools, control flow)
- You want to test with different LLM responses
- Test expectations change

```bash
# Delete old recordings and re-record
rm tests/integration/recordings/*.json
RECORD_MODE=true pytest tests/integration/ -v
```

#### How It Works

The record/replay pattern uses `tests/integration/llm_recorder.py`:
- **Recording**: Patches LLM API calls to save responses to JSON files in `tests/integration/recordings/`
- **Replay**: Reads saved responses from JSON and returns them without API calls
- Each test gets its own JSON file (e.g., `test_full_interview_flow.json`)
- Responses include text, function calls, and metadata

**Benefits:**
- **Cost Savings**: Only pay for LLM once during recording
- **Speed**: Tests run 5x faster without real API calls (~4s vs ~20s)
- **Determinism**: Same responses every time, no flaky tests
- **Debugging**: Inspect exact LLM responses in JSON files

### Run All Tests

```bash
# Run all tests (unit + integration in replay mode)
pytest -v

# Run unit tests only with coverage
pytest tests/ --ignore=tests/integration/ --cov=interview_agent --cov-report=term-missing

# See test coverage for entire module
pytest --cov=interview_agent --cov-report=term-missing

# See test coverage for agent.py only
pytest tests/test_agent.py --cov=interview_agent.agent --cov-report=term-missing

pytest tests/interview_types/system_design/test_phase_agent.py --cov=interview_agent.interview_types.system_design.phase_agent --cov-report=term-missing
```

## Code Quality

```bash
# Run linter
ruff check .

# Format code
ruff format .

# Pre-commit hooks (auto-formats on commit)
pre-commit install
```

## High-Level Design

Multi-tier agent orchestration with deterministic control flow:

**Agent Hierarchy:**
```
RootCustomAgent (root.py)
  ├─ routing_agent: Collects company/interview type via tools
  └─ SystemDesignOrchestrator (orchestrator.py)
      ├─ intro_agent: Welcomes candidate, explains format
      ├─ SystemDesignAgent (system_design_agent.py): Company-specific orchestrator
      │   └─ PhaseAgent (phase_agent.py): LLM-driven phase conductor
      │       └─ CompanyTools (tools/amazon_tools.py): Phase definitions & context
      └─ closing_agent: Wraps up, provides next steps
```

**Interview Flow:**
1. Root agent checks routing state → delegates to routing_agent if missing
2. Routing agent collects company/type → saves via `set_routing_decision()` tool
3. Root agent delegates to SystemDesignOrchestrator
4. Orchestrator runs: intro → design (multi-phase) → closing
5. Design agent loads company tools → iterates through phases
6. Phase agent conducts LLM conversation → calls `mark_phase_complete()` when done

## Structure

```
interview_agent/
├── shared/
│   ├── agents/          # Reusable agents (intro, closing)
│   ├── prompts/         # External prompt templates
│   ├── schemas/         # Pydantic schemas
│   └── constants.py     # Shared constants
├── interview_types/
│   └── system_design/
│       ├── orchestrator.py      # Main interview orchestrator
│       ├── system_design_agent.py
│       ├── phase_agent.py
│       └── tools/               # Company-specific tools & phases
└── root.py              # Root agent with deterministic routing

tests/
├── integration/
│   ├── llm_recorder.py  # Record/replay infrastructure
│   ├── recordings/      # Saved LLM responses
│   └── test_interview_flow.py
├── shared/
│   └── agents/          # Unit tests for shared agents
└── interview_types/
    └── system_design/
        ├── tools/       # Tests for company tools
        └── ...          # Tests for orchestrators
```

## Features

- **Deterministic routing**: Tool-based company/interview type detection
- **Tool-based state management**: Uses ADK tools for state persistence
- **Custom BaseAgent**: Explicit control flow to reduce LLM calls
- **External prompts**: Prompts stored in text files with constant injection
- **Record/Replay Testing**: Integration tests without ongoing API costs
