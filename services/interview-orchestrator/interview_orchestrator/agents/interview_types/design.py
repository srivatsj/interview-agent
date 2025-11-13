"""System design interview agent."""

from google.adk.agents import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools import ToolContext

from ...shared.agent_registry import AgentProviderRegistry
from ...shared.constants import get_gemini_model
from ...shared.prompts.prompt_loader import load_prompt


def _mark_design_complete(tool_context: ToolContext) -> str:
    """Mark design interview complete and transition to closing.

    Returns:
        Confirmation message
    """
    tool_context.state["interview_phase"] = "closing"
    return "Design interview complete. Moving to closing."


def _get_design_instruction(ctx: ReadonlyContext) -> str:
    """Get system design instruction with context."""
    routing = ctx.session.state.get("routing_decision", {})
    candidate_info = ctx.session.state.get("candidate_info", {})
    question = ctx.session.state.get("interview_question", "")

    return load_prompt(
        "design_agent.txt",
        company=routing.get("company", "COMPANY"),
        interview_type="system_design",
        candidate_name=candidate_info.get("name", "candidate"),
        interview_question=question,
    )


# System design interview agent
design_interview_agent = Agent(
    name="design_interview_agent",
    model=get_gemini_model(),
    description="Conducts system design interview",
    instruction=_get_design_instruction,
    tools=[
        *AgentProviderRegistry.get_remote_agent_tools("system_design"),
        _mark_design_complete,
    ],
)
