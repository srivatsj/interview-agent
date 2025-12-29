"""POC: Sequential Agent Pattern for deterministic flow control.

This pattern replaces transfer_to_agent with Sequential/Parallel agents for
more predictable, easier-to-debug flow control.
"""

from google.adk.agents import Agent, SequentialAgent
from google.adk.tools import ToolContext

from ..shared.constants import get_gemini_model


def collect_user_info(name: str, topic: str, tool_context: ToolContext) -> str:
    """Collect user information (simulates intro phase).

    CRITICAL: Call this when you have the user's name and topic.

    Args:
        name: User's name
        topic: Topic they want to discuss
        tool_context: Tool execution context

    Returns:
        Confirmation message
    """
    tool_context.state["user_name"] = name
    tool_context.state["user_topic"] = topic
    return f"Info saved: {name} wants to discuss {topic}"


def provide_expert_response(query: str, tool_context: ToolContext) -> str:
    """Provide expert response (simulates remote agent call).

    CRITICAL: Use this for ALL user questions about their topic.

    Args:
        query: User's question
        tool_context: Tool execution context

    Returns:
        Expert response
    """
    # Mark that expert was called (for testing)
    tool_context.state["expert_called"] = True

    # Simulate expert response
    topic = tool_context.state.get("user_topic", "general")
    return f"Expert response about {topic}: Here's detailed guidance on '{query}'"


# Agent 1: Info Collector (like intro_agent)
info_collector = Agent(
    name="info_collector",
    model=get_gemini_model(),
    description="Collects user name and topic",
    instruction="""Collect 2 pieces of information:
1. User's name
2. Topic they want to discuss

As SOON as you have both, call collect_user_info tool.
DO NOT proceed to discussion - just collect info.""",
    tools=[collect_user_info],
    output_key="intro_complete"
)

# Agent 2: Expert Consultant (like design_agent with forced tool use)
expert_consultant = Agent(
    name="expert_consultant",
    model=get_gemini_model(),
    description="Provides expert guidance on user's topic",
    instruction="""You help {user_name} with {user_topic}.

CRITICAL: Before responding to ANY user question:
1. Call provide_expert_response with their question
2. Present the expert's answer naturally

You MUST use the tool for every response.""",
    tools=[provide_expert_response],
)


# Root: Sequential Agent (deterministic flow)
# This GUARANTEES: info_collector runs THEN expert_consultant
# No transfer_to_agent needed!
sequential_root = SequentialAgent(
    name="sequential_conversation",
    description="Handles conversation with deterministic sequential flow",
    sub_agents=[
        info_collector,      # Always runs first
        expert_consultant,   # Always runs second
    ]
)
