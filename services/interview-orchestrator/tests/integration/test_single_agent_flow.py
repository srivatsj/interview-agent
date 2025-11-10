"""Integration test for single-agent interview flow.

Tests the complete interview flow through all phases using text messages.
"""

import asyncio

import pytest
from google.adk.agents import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types

from interview_orchestrator.interview_types.system_design.design_agent_tool import (
    initialize_design_phase,
    mark_design_complete,
)
from interview_orchestrator.root_agent import get_dynamic_instruction
from interview_orchestrator.shared.tools.closing_tools import mark_interview_complete
from interview_orchestrator.shared.tools.intro_tools import save_candidate_info
from interview_orchestrator.shared.tools.routing_tools import set_routing_decision

# Create test agent with text model (not Live API audio model)
test_agent = Agent(
    name="interview_agent",
    model="gemini-2.0-flash",  # Standard text model for testing
    description="Conducts technical interviews with multi-phase flow",
    instruction=get_dynamic_instruction,
    tools=[
        set_routing_decision,
        save_candidate_info,
        initialize_design_phase,
        mark_design_complete,
        mark_interview_complete,
    ],
)


@pytest.mark.asyncio
async def test_state_transitions():
    """Test that state transitions happen correctly."""
    runner = InMemoryRunner(agent=test_agent, app_name="test_transitions")

    user_id = "user1"
    session_id = "session1"

    # Create session first
    await runner.session_service.create_session(
        app_name="test_transitions", user_id=user_id, session_id=session_id
    )

    # Test routing → intro
    for _ in runner.run(
        user_id=user_id,
        session_id=session_id,
        new_message=types.Content(parts=[types.Part(text="I want a Meta system design interview")]),
    ):
        pass

    session = await runner.session_service.get_session(
        app_name="test_transitions", user_id=user_id, session_id=session_id
    )
    assert session.state["interview_phase"] == "intro"
    assert session.state["routing_decision"]["company"] == "meta"

    # Test intro → design (be explicit with all 4 required fields)
    for _ in runner.run(
        user_id=user_id,
        session_id=session_id,
        new_message=types.Content(
            parts=[
                types.Part(
                    text="My name is Bob Lee, I have 3 years of experience in frontend development, "
                    "my primary domain is frontend, and I worked on social media apps. "
                    "Yes, I understand the format and I'm ready to begin!"
                )
            ]
        ),
    ):
        pass

    session = await runner.session_service.get_session(
        app_name="test_transitions", user_id=user_id, session_id=session_id
    )
    assert session.state["interview_phase"] == "design"
    assert session.state["candidate_info"]["name"] == "Bob Lee"

    print("✓ State transitions verified")


if __name__ == "__main__":
    # Run test directly
    asyncio.run(test_state_transitions())
