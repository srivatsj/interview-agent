"""Coding interview agent."""

import os

from google.adk.agents import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.code_executors import BuiltInCodeExecutor
from google.adk.tools import ToolContext

from ...shared.agent_registry import AgentProviderRegistry
from ...shared.prompts.prompt_loader import load_prompt


def _mark_coding_complete(tool_context: ToolContext) -> str:
    """Mark coding interview complete and transition to closing.

    Returns:
        Confirmation message
    """
    tool_context.state["interview_phase"] = "closing"
    return "Coding interview complete. Moving to closing."


def _get_coding_instruction(ctx: ReadonlyContext) -> str:
    """Get coding interview instruction with context."""
    routing = ctx.session.state.get("routing_decision", {})
    candidate_info = ctx.session.state.get("candidate_info", {})
    question = ctx.session.state.get("interview_question", "")

    return load_prompt(
        "coding_agent.txt",
        company=routing.get("company", "COMPANY"),
        interview_type="coding",
        candidate_name=candidate_info.get("name", "candidate"),
        interview_question=question,
    )


# Coding interview agent with code executor
coding_interview_agent = Agent(
    name="coding_interview_agent",
    model=os.getenv("AGENT_MODEL", "gemini-2.0-flash-exp"),
    description="Conducts coding interview with code execution capabilities",
    instruction=_get_coding_instruction,
    code_executor=BuiltInCodeExecutor(),
    tools=[*AgentProviderRegistry.get_remote_agent_tools("coding"), _mark_coding_complete],
)
