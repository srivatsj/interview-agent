# TODO: Phase-Based Evaluation & Multi-Phase Design Interviews

## Overview

Enhance the design phase with structured multi-phase interviews that include evaluation and progression through specific design stages (problem clarification → requirements → data design → API design → high-level design).

Currently, the design phase is a single continuous conversation. This TODO outlines how to add structured phases with evaluation, similar to the old multi-phase pattern but using the current single-agent architecture.

---

## Current State

**What We Have:**
- Single-agent pattern with dynamic instruction
- Tool-based phase transitions: routing → intro → design → closing → done
- Design phase is one continuous conversation
- Remote agents (A2A) and local default tools
- Bidirectional WebSocket with user interruptions

**Design Phase Flow:**
```python
# Current flow
1. initialize_design_phase() → loads question
2. User discusses design freely
3. mark_design_complete() → moves to closing
```

---

## Proposed Enhancement: Multi-Phase Design

### Goal

Break the design phase into structured sub-phases with evaluation criteria:

```
DESIGN PHASE
    ├── Problem Clarification (evaluate coverage of: scale, latency, features)
    ├── Requirements Gathering (evaluate: functional, non-functional, constraints)
    ├── Data Design (evaluate: schema, database choice, sharding)
    ├── API Design (evaluate: endpoints, request/response, protocols)
    └── High-Level Design (evaluate: components, data flow, scalability)
```

### Benefits

1. **Structured Guidance**: Guide candidates through proper system design process
2. **Granular Evaluation**: Evaluate each phase separately for better feedback
3. **Progress Tracking**: Track which phases are complete vs in-progress
4. **Company-Specific**: Different companies can have different phase structures
5. **Better Assessment**: More detailed rubrics per phase

---

## Implementation Approach

### Option 1: State-Driven Sub-Phases (Recommended)

Continue using single-agent pattern with finer-grained state tracking.

#### State Schema Enhancement

```python
# Add to session state
state = {
    "interview_phase": "design",  # Main phase
    "design_sub_phase": "problem_clarification",  # Sub-phase
    "design_sub_phase_idx": 0,  # Current sub-phase index
    "design_phases_completed": [],  # List of completed sub-phase IDs
    "design_phases": [  # Phase structure from provider
        {
            "id": "problem_clarification",
            "name": "Problem Clarification",
            "description": "...",
            "keywords": ["scale", "users", "QPS", "latency"]
        },
        # ... more phases
    ]
}
```

#### Modified Design Phase Instruction

```python
# interview_orchestrator/root_agent.py
def get_dynamic_instruction(ctx: ReadonlyContext) -> str:
    phase = ctx.session.state.get("interview_phase", "routing")

    if phase == "design":
        # Get current sub-phase
        sub_phase = ctx.session.state.get("design_sub_phase", "problem_clarification")
        design_phases = ctx.session.state.get("design_phases", [])

        # Find current phase details
        current_phase_info = next(
            (p for p in design_phases if p["id"] == sub_phase),
            design_phases[0] if design_phases else None
        )

        if not current_phase_info:
            # Fallback to single-phase design
            return load_prompt("design_phase.txt", ...)

        # Load sub-phase specific prompt
        return load_prompt(
            "design_sub_phase.txt",
            company=company,
            candidate_name=candidate_name,
            interview_question=interview_question,
            phase_name=current_phase_info["name"],
            phase_description=current_phase_info["description"],
            phase_keywords=current_phase_info["keywords"],
        )
```

#### New Tools for Sub-Phase Management

```python
# interview_orchestrator/interview_types/system_design/design_agent_tool.py

async def get_design_phases(tool_context: ToolContext) -> str:
    """
    Get structured phases for the design interview.

    Called automatically when design phase starts.
    Fetches phase structure from company-specific provider.
    """
    routing = tool_context.state.get("routing_decision", {})
    company = routing.get("company", "default")

    provider = CompanyFactory.get_tools(company, "system_design")

    # Get phases from provider
    phases = await provider.get_phases()
    # Returns: [
    #   {"id": "problem_clarification", "name": "Problem Clarification", ...},
    #   {"id": "requirements", "name": "Requirements Gathering", ...},
    #   ...
    # ]

    tool_context.state["design_phases"] = phases
    tool_context.state["design_sub_phase"] = phases[0]["id"]
    tool_context.state["design_sub_phase_idx"] = 0
    tool_context.state["design_phases_completed"] = []

    return f"Design phases loaded: {len(phases)} phases"


async def evaluate_design_phase(tool_context: ToolContext) -> str:
    """
    Evaluate current design sub-phase completion.

    Called by LLM when it thinks the candidate has covered the phase.
    Fetches evaluation from company-specific provider.
    """
    routing = tool_context.state.get("routing_decision", {})
    company = routing.get("company", "default")

    provider = CompanyFactory.get_tools(company, "system_design")

    # Get current phase and conversation
    current_phase = tool_context.state.get("design_sub_phase")
    # Extract conversation history from session events
    conversation = _extract_conversation_from_session(tool_context)

    # Call provider for evaluation
    evaluation = await provider.evaluate_phase(current_phase, conversation)
    # Returns: {
    #   "decision": "next_phase" | "continue",
    #   "score": 7.5,
    #   "feedback": "Good coverage of...",
    #   "gaps": ["sharding strategy", "backup"]
    # }

    if evaluation["decision"] == "next_phase":
        # Move to next phase
        current_idx = tool_context.state.get("design_sub_phase_idx", 0)
        phases = tool_context.state.get("design_phases", [])

        # Mark current phase complete
        tool_context.state["design_phases_completed"].append(current_phase)

        # Move to next phase or complete
        if current_idx + 1 < len(phases):
            next_idx = current_idx + 1
            tool_context.state["design_sub_phase"] = phases[next_idx]["id"]
            tool_context.state["design_sub_phase_idx"] = next_idx

            return (
                f"Phase '{current_phase}' complete (score: {evaluation['score']}/10). "
                f"Moving to '{phases[next_idx]['name']}'"
            )
        else:
            # All phases done - mark design complete
            tool_context.state["design_complete"] = True
            tool_context.state["interview_phase"] = "closing"

            return "All design phases complete! Moving to closing remarks."
    else:
        # Phase not complete - provide feedback
        return (
            f"Phase '{current_phase}' needs more discussion. "
            f"Score: {evaluation['score']}/10. "
            f"Gaps: {', '.join(evaluation['gaps'])}. "
            f"Continue discussing these areas."
        )


def _extract_conversation_from_session(tool_context: ToolContext) -> list[dict]:
    """Extract conversation history for evaluation."""
    # Implementation: Parse session events to get user/agent messages
    # since design phase started
    pass
```

#### New Prompt Template

```
# interview_orchestrator/shared/prompts/design_sub_phase.txt

<role>
You are conducting the **{phase_name}** phase of a system design interview for {company}.
</role>

<interview_question>
{interview_question}
</interview_question>

<current_phase>
Phase: {phase_name}
Description: {phase_description}

Key topics to cover:
{phase_keywords}
</current_phase>

<instructions>
1. Guide the candidate through {phase_name}
2. Ask probing questions about: {phase_keywords}
3. Ensure they cover all key topics before moving on
4. When you believe the candidate has adequately covered this phase:
   - Call evaluate_design_phase() to check if they can progress
   - If approved, you'll automatically move to the next phase
   - If not, continue discussing the gaps identified
</instructions>

<tools_available>
- evaluate_design_phase(): Call when candidate seems ready to move to next phase
</tools_available>

<conversation_style>
- Be encouraging and supportive
- Ask one question at a time
- Provide hints if candidate is stuck
- Don't rush - let them think deeply
</conversation_style>
```

#### Provider Protocol Update

```python
# interview_orchestrator/shared/agent_providers/protocol.py

class InterviewAgentProtocol(Protocol):
    """Protocol for interview agents (local or remote)."""

    async def start_interview(self, interview_type: str, candidate_info: dict) -> dict:
        """Initialize interview session."""
        ...

    async def get_question(self) -> str:
        """Get system design question."""
        ...

    async def get_phases(self) -> list[dict]:
        """
        Get structured phases for the interview.

        Returns:
            List of phase dictionaries with structure:
            [
                {
                    "id": "problem_clarification",
                    "name": "Problem Clarification",
                    "description": "Clarify functional and non-functional requirements",
                    "keywords": ["scale", "users", "QPS", "latency", "availability"]
                },
                ...
            ]
        """
        ...

    async def evaluate_phase(self, phase_id: str, conversation_history: list) -> dict:
        """
        Evaluate if candidate has adequately covered the phase.

        Args:
            phase_id: ID of current phase (e.g., "problem_clarification")
            conversation_history: List of messages since phase started

        Returns:
            {
                "decision": "next_phase" | "continue",
                "score": 7.5,  # 0-10 scale
                "feedback": "Good coverage of scale requirements...",
                "gaps": ["latency requirements", "failure scenarios"]
            }
        """
        ...
```

---

## Implementation Tasks

### Phase 1: Update Default Tools (Local)

**File:** `interview_orchestrator/interview_types/system_design/tools/default_tools.py`

```python
class DefaultSystemDesignTools:
    """Free tier with basic phase structure and keyword-based evaluation."""

    PHASES = [
        {
            "id": "problem_clarification",
            "name": "Problem Clarification",
            "description": "Clarify requirements, scale, and constraints",
            "keywords": ["users", "QPS", "scale", "latency", "availability", "consistency"]
        },
        {
            "id": "requirements",
            "name": "Requirements Gathering",
            "description": "Define functional and non-functional requirements",
            "keywords": ["features", "API", "constraints", "SLA", "throughput"]
        },
        {
            "id": "data_design",
            "name": "Data Design",
            "description": "Design data model, storage, and schemas",
            "keywords": ["database", "schema", "SQL", "NoSQL", "sharding", "replication"]
        },
        {
            "id": "api_design",
            "name": "API Design",
            "description": "Design REST/RPC APIs and contracts",
            "keywords": ["endpoint", "REST", "gRPC", "request", "response", "HTTP"]
        },
        {
            "id": "hld",
            "name": "High-Level Design",
            "description": "Design system architecture and components",
            "keywords": ["load balancer", "cache", "queue", "CDN", "microservices", "architecture"]
        }
    ]

    async def get_phases(self) -> list[dict]:
        """Return phase structure."""
        return self.PHASES

    async def evaluate_phase(self, phase_id: str, conversation: list) -> dict:
        """Simple keyword-based evaluation."""
        # Find phase
        phase = next((p for p in self.PHASES if p["id"] == phase_id), None)
        if not phase:
            return {"decision": "continue", "score": 0, "gaps": []}

        # Calculate keyword coverage
        text = " ".join([msg["content"].lower() for msg in conversation])
        keywords = phase["keywords"]

        covered = sum(1 for kw in keywords if kw.lower() in text)
        coverage = covered / len(keywords)
        score = coverage * 10  # 0-10 scale

        # Decision threshold: 60% coverage
        if coverage >= 0.6:
            return {
                "decision": "next_phase",
                "score": score,
                "feedback": f"Good coverage of {phase['name']}",
                "gaps": []
            }
        else:
            gaps = [kw for kw in keywords if kw.lower() not in text]
            return {
                "decision": "continue",
                "score": score,
                "feedback": f"Need more discussion on {phase['name']}",
                "gaps": gaps
            }
```

### Phase 2: Update Remote Providers (A2A)

Remote agents (Google, Meta) will implement `get_phases()` and `evaluate_phase()` endpoints:

**Google Agent Example:**
```python
# services/google-agent/google_agent/server.py

@app.post("/get_phases")
async def get_phases():
    """Return Google-specific design phases."""
    return {
        "phases": [
            {
                "id": "problem_understanding",
                "name": "Problem Understanding",
                "description": "Understand user needs and system goals",
                "keywords": ["users", "goals", "constraints", "non-goals"]
            },
            # ... Google-specific phases
        ]
    }

@app.post("/evaluate_phase")
async def evaluate_phase(request: dict):
    """Use LLM to evaluate phase completion with Google criteria."""
    phase_id = request["phase_id"]
    conversation = request["conversation_history"]

    # Use Gemini to evaluate based on Google's rubric
    evaluation = await evaluate_with_gemini(
        phase_id=phase_id,
        conversation=conversation,
        company_rubric="google_system_design"
    )

    return evaluation
```

### Phase 3: Update Root Agent

**File:** `interview_orchestrator/root_agent.py`

Add sub-phase handling to `get_dynamic_instruction()`.

### Phase 4: Testing

Create tests for:
- Multi-phase progression
- Phase evaluation (pass/fail)
- State transitions between sub-phases
- Conversation extraction for evaluation

---

## Migration Strategy

**Backward Compatible:**
- Keep existing single-phase design flow
- Only activate multi-phase if `design_phases` exists in state
- Providers can opt-in by implementing `get_phases()`
- Default behavior: single phase (current behavior)

**Gradual Rollout:**
1. Implement for default tools (free tier)
2. Test with integration tests
3. Add to one remote agent (e.g., Google)
4. Expand to other remote agents

---

## Future Enhancements

### 1. Dynamic Phase Ordering
Allow LLM to suggest phase order based on candidate's approach.

### 2. Phase Skipping
Let candidates skip phases if not relevant (e.g., skip API design for data pipeline).

### 3. Parallel Phases
Some phases could be discussed in parallel (e.g., data + API design together).

### 4. LLM-Based Evaluation
Use LLM for evaluation instead of keyword matching (more sophisticated).

### 5. Real-Time Hints
Provide hints during phase if candidate is stuck.

---

## Files to Modify

```
interview_orchestrator/
├── root_agent.py                         # Add sub-phase to get_dynamic_instruction()
├── interview_types/system_design/
│   ├── design_agent_tool.py              # Add get_design_phases(), evaluate_design_phase()
│   └── tools/default_tools.py            # Implement get_phases(), evaluate_phase()
├── shared/
│   ├── prompts/
│   │   └── design_sub_phase.txt          # NEW: Sub-phase prompt template
│   └── agent_providers/
│       └── protocol.py                   # Add get_phases(), evaluate_phase() to protocol

tests/
├── interview_types/system_design/
│   └── test_design_agent_tool.py         # Add tests for new tools
└── integration/
    └── test_multi_phase_design.py        # NEW: Integration test for phase progression
```

---

## Priority

**P2 (Nice to Have)**
- Current single-phase design works well
- Multi-phase adds structure but not critical for MVP
- Implement after:
  - Frontend integration with bidirectional audio
  - Remote agent deployment
  - Basic evaluation and feedback

---

## Related Issues

- User interruptions (✅ Implemented via BIDI streaming)
- Remote agent integration (✅ Implemented via A2A protocol)
- Session state persistence (✅ Using InMemorySessionService)

---

## Questions to Resolve

1. **Phase Granularity**: Are 5 phases too many? Should we have 3-4?
2. **Evaluation Strictness**: What threshold for phase progression (60%? 70%?)?
3. **Candidate Control**: Should candidates be able to say "I want to skip to API design"?
4. **Time Limits**: Should each phase have a time limit?
5. **Retries**: If phase evaluation fails, how many chances to continue discussing?

---

**Last Updated:** 2025-11-09
**Status:** Planned (Not Started)
**Owner:** Future contributor
