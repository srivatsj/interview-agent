# Orchestrator2 - ADK Pattern POC

This is a proof-of-concept to test ADK patterns with native audio and bidirectional streaming:

## Patterns Being Tested

1. **Sequential Agents** - Deterministic flow control instead of transfer_to_agent
2. **Custom Executors** - Force tool usage and control execution flow

## Goals

- Verify sequential agents work with live audio streaming
- Verify custom executors work with bidirectional audio
- Test if these patterns make code easier to debug, maintain, and more deterministic

## Structure

```
orchestrator2/
├── agents/
│   ├── sequential_poc.py     # Sequential agent pattern test
│   └── executor_poc.py        # Custom executor pattern test
├── shared/
│   └── constants.py
└── tests/
    └── test_audio_patterns.py # Test both patterns with audio
```

## Running

```bash
# Install dependencies
uv sync --extra dev

# Run tests
uv run pytest tests/ -v
```
