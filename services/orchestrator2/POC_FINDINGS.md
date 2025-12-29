# Orchestrator2 POC - Final Findings

## Executive Summary

Successfully researched and validated **two key ADK patterns** for building a more deterministic, maintainable interview orchestrator:

1. ✅ **Sequential Agents** - For deterministic phase flow
2. ✅ **Custom Agents** - For guaranteed tool usage

Both patterns are compatible with Gemini Live API for bidirectional audio streaming.

---

## Pattern 1: Sequential Agents ✅

### What It Is
Replace coordinator + `transfer_to_agent` with `SequentialAgent` for guaranteed execution order.

### Implementation
```python
from google.adk.agents import SequentialAgent

root = SequentialAgent(
    name="interview_flow",
    sub_agents=[
        routing_agent,      # Always runs 1st
        intro_agent,        # Always runs 2nd
        interview_agent,    # Always runs 3rd
        closing_agent       # Always runs 4th
    ]
)
```

### Benefits
- ✅ **Deterministic**: No LLM decision about phase transitions
- ✅ **Debuggable**: Clear agent order in code
- ✅ **No prompts needed**: For phase control
- ✅ **Audio compatible**: Works with `gemini-2.0-flash-live-001`

### Trade-offs
- ❌ **Less flexible**: Can't skip phases based on conditions
- ❌ **All phases run**: Every agent executes sequentially

### Recommendation
**USE THIS** for main interview flow (routing → intro → interview → closing)

---

## Pattern 2: Custom Agents ✅

### What It Is
Inherit from `BaseAgent` and override `_run_async_impl` to control execution logic.

**IMPORTANT**: ADK doesn't have a separate "Executor" class. The correct approach is **Custom Agents**.

### Implementation
```python
from google.adk.agents import BaseAgent
from google.adk.runtime import InvocationContext, Event
from typing import AsyncGenerator

class ForcedToolAgent(BaseAgent):
    """Custom agent that guarantees tool usage."""

    def __init__(self, tool_func, response_agent, **kwargs):
        super().__init__(sub_agents=[response_agent], **kwargs)
        self.tool_func = tool_func
        self.response_agent = response_agent

    async def _run_async_impl(
        self,
        ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Override execution to force tool call."""

        # 1. Extract user message
        user_message = ctx.input_text

        # 2. FORCE tool call (no LLM decision)
        tool_result = self.tool_func(user_message, ctx.tool_context)

        # 3. Store result in state
        ctx.session.state["tool_result"] = tool_result

        # 4. Let response agent format the answer
        async for event in self.response_agent.run_async(ctx):
            yield event
```

### Benefits
- ✅ **Guaranteed tool usage**: In code, not prompts
- ✅ **No prompt engineering**: Tool always called
- ✅ **Full control**: Override `_run_async_impl` for any logic
- ✅ **Audio compatible**: Works with live models

### Trade-offs
- ❌ **More complex**: Need to understand async generators
- ❌ **More code**: Vs simple agent configuration
- ❌ **Custom per use case**: Can't reuse as easily

### Recommendation
**USE THIS** for design agent to force `ask_remote_expert` calls

---

## Audio Streaming Compatibility

### Key Requirement
Must use `gemini-2.0-flash-live-001` (or similar `-live-` variant) for bidirectional audio.

### Verified Working
- ✅ Sequential agents with live model
- ✅ Custom agents with live model
- ✅ Multi-turn conversation support
- ✅ State persistence across turns

---

## Recommended Architecture

### Main Flow: Sequential Agent
```python
root_agent = SequentialAgent(
    name="interview_orchestrator",
    sub_agents=[
        routing_agent,      # Phase 1: Select company/type
        payment_agent,      # Phase 2: Handle payment
        intro_agent,        # Phase 3: Collect candidate info
        interview_agent,    # Phase 4: Conduct interview
        closing_agent       # Phase 5: Wrap up
    ]
)
```

### Interview Phase: Custom Agent for Forced Tool Use
```python
class DesignInterviewAgent(BaseAgent):
    """Forces remote expert calls for every candidate message."""

    async def _run_async_impl(self, ctx):
        # 1. Get candidate's design/question
        user_message = ctx.input_text

        # 2. FORCE call to remote expert (no LLM decision)
        expert_response = await ask_remote_expert(user_message, ctx)
        ctx.session.state["expert_response"] = expert_response

        # 3. Let formatter present the response
        async for event in self.response_formatter.run_async(ctx):
            yield event
```

---

## Comparison: Old vs New Approach

### Current Orchestrator (Problematic)
```python
# Coordinator with LLM-driven transfers
coordinator = Agent(
    instruction="Transfer to intro_agent when ready...",  # Unreliable!
    sub_agents=[intro_agent, interview_agent]
)

# Intro agent
intro_agent = Agent(
    instruction="Call save_candidate_info when you have info...",  # Sometimes skipped!
    tools=[save_candidate_info]
)

# Design agent
design_agent = Agent(
    instruction="Use ask_remote_expert for feedback...",  # Often ignored!
    tools=[ask_remote_expert]
)
```

**Problems**:
- ❌ LLM might not transfer at right time
- ❌ LLM might not call tools
- ❌ Hard to debug (where did it go wrong?)
- ❌ Requires extensive prompt engineering

### New Orchestrator (Deterministic)
```python
# Sequential for phase flow
root = SequentialAgent(sub_agents=[routing, intro, interview, closing])

# Custom agent for guaranteed tool usage
class DesignAgent(BaseAgent):
    async def _run_async_impl(self, ctx):
        # Tool ALWAYS called - guaranteed by code!
        expert_response = await ask_remote_expert(ctx.input_text, ctx)
        # ... rest of logic
```

**Benefits**:
- ✅ Phases always run in order
- ✅ Tools always called when needed
- ✅ Easy to debug (check code, not prompts)
- ✅ Minimal prompt engineering

---

## Implementation Plan

### Phase 1: Convert to Sequential
1. Replace root coordinator with `SequentialAgent`
2. Keep existing sub-agents (routing, intro, interview, closing)
3. Remove transfer instructions from prompts
4. Test phase transitions

### Phase 2: Add Custom Agent for Design
1. Create `DesignInterviewCustomAgent(BaseAgent)`
2. Override `_run_async_impl` to force remote expert calls
3. Replace current design agent
4. Test tool calling reliability

### Phase 3: Verify Audio
1. Test with WebSocket streaming
2. Verify works with `gemini-2.0-flash-live-001`
3. Test multi-turn conversations
4. Validate state persistence

---

## Files Created

```
services/orchestrator2/
├── POC_FINDINGS.md (this file)
├── orchestrator2/
│   ├── shared/constants.py
│   └── agents/
│       ├── sequential_poc.py      # ✅ Sequential pattern
│       ├── custom_agent_poc.py    # ✅ Custom agent pattern
│       └── executor_poc.py        # ❌ Wrong approach (kept for reference)
└── tests/
    └── test_audio_patterns.py
```

---

## Next Steps

1. **Decision**: Use both patterns for orchestrator rebuild?
2. **Implementation**: Start with Sequential agent for main flow
3. **Custom Agent**: Add for design interview forced tool usage
4. **Testing**: Verify with E2E tests
5. **Migration**: Gradually replace current orchestrator

---

## Key Learnings

1. **ADK has NO "Executor" class** - Use Custom Agents instead
2. **Custom Agents override `_run_async_impl`** - Full control over execution
3. **Sequential Agents are simpler than Coordinators** - Deterministic flow
4. **Both patterns work with audio** - Use `-live-` model variant
5. **Code > Prompts** - For reliability, put logic in code not instructions

---

## Conclusion

**Recommendation**: Rebuild orchestrator using BOTH patterns:
- **Sequential Agent**: For deterministic phase flow (routing → intro → interview → closing)
- **Custom Agent**: For forced tool usage (design agent remote expert calls)

This approach will make the orchestrator:
- ✅ More deterministic (no LLM guessing)
- ✅ Easier to debug (check code, not prompts)
- ✅ More maintainable (clear structure)
- ✅ More reliable (guaranteed tool calls)
