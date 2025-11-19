"""Coding interview agent."""

import logging

from google.adk.agents import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.code_executors import BuiltInCodeExecutor
from google.adk.tools import ToolContext

from ...shared.constants import get_gemini_model
from ...shared.infra.a2a.agent_registry import AgentProviderRegistry
from ...shared.infra.a2a.remote_client import call_remote_skill
from ...shared.prompts.prompt_loader import load_prompt

logger = logging.getLogger(__name__)


async def ask_remote_expert(query: str, tool_context: ToolContext) -> str:
    """Get feedback from company-specific remote expert agent.

    Phase 1: Calls remote agent without payment verification.
    Phase 2: Will add payment_proof verification.

    Args:
        query: Coding question or solution to get feedback on
        tool_context: Tool execution context

    Returns:
        Expert feedback from remote agent
    """
    # Get company from routing decision
    routing = tool_context.state.get("routing_decision", {})
    company = routing.get("company")

    if not company:
        return "No company selected. Cannot access remote expert."

    # Get remote agent URL
    agent_url = AgentProviderRegistry.get_agent_url(company, "coding")
    if not agent_url:
        return f"Remote expert not available for {company}."

    # Call remote agent (Phase 1 - no payment proof yet)
    try:
        response = await call_remote_skill(agent_url=agent_url, text=query, data={})
        # Extract text response from remote agent
        return response.get("message", str(response))
    except Exception as e:
        logger.error(f"Failed to call remote expert at {agent_url}: {e}")
        return f"Error contacting {company} expert. Continuing with general guidance."


def _mark_coding_complete(tool_context: ToolContext) -> str:
    """Mark coding interview complete and transition to closing."""
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
    model=get_gemini_model(),
    description="Conducts coding interview with code execution capabilities",
    instruction=_get_coding_instruction,
    code_executor=BuiltInCodeExecutor(),
    tools=[
        ask_remote_expert,
        _mark_coding_complete,
    ],
)
