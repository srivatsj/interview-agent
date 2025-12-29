# Orchestrator2 POC Summary

## Status: IN PROGRESS

Created proof-of-concept for two key ADK patterns to improve interview orchestrator:

### 1. ✅ Sequential Agent Pattern (`sequential_poc.py`)

**Goal**: Replace `transfer_to_agent` with deterministic Sequential agents for predictable flow.

**Implementation**:
```python
# Instead of coordinator + transfer_to_agent:
SequentialAgent(
    sub_agents=[
        info_collector,      # Phase 1: ALWAYS runs first
        expert_consultant,   # Phase 2: ALWAYS runs second
    ]
)
```

**Benefits**:
- ✅ Deterministic phase order (no LLM decision about when to switch)
- ✅ Easier to debug (clear agent sequence in code)
- ✅ No prompt engineering for phase transitions
- ✅ Compatible with audio/live streaming (uses `gemini-2.0-flash-live-001`)

**Test Status**: Needs session API fix (`app_name` and `user_id` params)

### 2. ⚠️ Custom Executor Pattern (`executor_poc.py`)

**Goal**: Force tool usage without prompt engineering.

**Implementation Attempt**:
```python
class ForcedToolExecutor(Executor):
    async def execute(self, request, context):
        # Force tool call before LLM response
        tool_result = await self.tool_func(user_message, context.tool_context)
        # Let LLM format the response
        return await super().execute(modified_request, context)
```

**Issue Found**:
- ❌ `google.adk.agents.executor` module doesn't exist in ADK 1.16.0
- ❌ Need to find correct ADK executor API or alternative pattern

**Alternative Approaches to Explore**:
1. Subclass `Agent` and override `generate_content()`
2. Use middleware/hooks if ADK provides them
3. Use Sequential pattern with dedicated "tool caller" agent
4. Check if newer ADK version has executor API

### 3. Audio/Streaming Compatibility

**Verified**:
- ✅ Using `gemini-2.0-flash-live-001` model (required for audio)
- ✅ Sequential agents can be configured with live model
- ⏳ Need to test actual audio streaming once basic patterns work

## Next Steps

1. **Fix Session Creation**: Update tests to use correct `create_session(app_name="test", user_id="test_user")`

2. **Fix Executor Pattern**:
   - Option A: Find correct ADK executor/middleware API
   - Option B: Implement workaround using Sequential agents
   - Option C: Override Agent.generate_content() directly

3. **Verify Audio**: Once tests pass, verify both patterns work with actual bidirectional audio

4. **Decision**: Based on test results, decide which pattern(s) to use for orchestrator rebuild

## Files Created

```
services/orchestrator2/
├── pyproject.toml
├── README.md
├── POC_SUMMARY.md (this file)
├── orchestrator2/
│   ├── __init__.py
│   ├── shared/
│   │   └── constants.py (model configuration)
│   └── agents/
│       ├── __init__.py
│       ├── sequential_poc.py (Sequential pattern ✅)
│       └── executor_poc.py (Executor pattern ⚠️)
└── tests/
    ├── __init__.py
    └── test_audio_patterns.py
```

## Key Learnings So Far

1. **Sequential Agents are simpler than Coordinators**: No `transfer_to_agent`, just list agents in order
2. **Model must be `-live-` variant**: `gemini-2.0-flash-live-001` for audio support
3. **ADK Executor API unclear**: May need alternative approach for forced tool usage
4. **Session requires metadata**: `app_name` and `user_id` are required parameters

## Recommendation

**Use Sequential Agents for orchestrator rebuild** - they provide:
- Deterministic flow (routing → intro → interview → closing)
- Easier debugging
- Works with audio
- Well-documented in ADK

**For forced tool usage** (design agent remote calls):
- Investigate ADK middleware/hooks
- Consider Sequential sub-pattern: [tool-caller-agent → response-formatter-agent]
- May need custom Agent subclass

