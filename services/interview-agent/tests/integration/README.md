# Integration Tests

## Overview
End-to-end integration test for complete interview CUJ with real LLM and agents.

## Test Coverage

### `test_complete_interview_journey`
**Complete interview flow from start to finish**

**What it tests:**
- ✅ Multi-turn routing conversation (2 messages)
- ✅ Multi-turn intro conversation (2 messages)
- ✅ Design Phase 1: Clarification (2 messages) - scale, QPS, latency, availability
- ✅ Design Phase 2: Design (2 messages) - database, API, architecture
- ✅ Design Phase 3: Tradeoffs (2 messages) - caching, load balancing, sharding
- ✅ Closing phase (conditional)
- ✅ State transitions and phase progression
- ✅ Tool calling (routing decision, candidate info)

**Metrics:**
- **LLM Calls:** 35
- **Record Time:** 198 seconds (~3.3 minutes)
- **Replay Time:** ~2 seconds

## Mock Provider

Uses `MockAmazonSystemDesignTools` with 3 phases instead of 6 for faster testing:
1. Clarification
2. Design
3. Tradeoffs

**Why mock?** Reduces test time by 50% while still validating phase progression, multi-turn conversations, and state management.

**What's NOT mocked:** All agents, LLM calls, state management, orchestration logic.

## Running Tests

**Record mode** (one-time, captures LLM responses):
```bash
RECORD_MODE=true pytest tests/integration/test_interview_flow.py -v
```

**Replay mode** (fast, uses recordings):
```bash
pytest tests/integration/test_interview_flow.py -v
```

## Coverage Summary

| What | Covered |
|------|---------|
| Multi-turn conversations | ✅ |
| Multi-conversation flow | ✅ |
| Phase progression (3 phases) | ✅ |
| State management | ✅ |
| Tool calling | ✅ |
| Complete CUJ | ✅ |
