"""System design interview agent."""

import os

from google.adk.agents import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.agents.remote_a2a_agent import AGENT_CARD_WELL_KNOWN_PATH, RemoteA2aAgent
from google.adk.tools import AgentTool, ToolContext

from ...shared.agent_registry import AgentProviderRegistry
from ...shared.prompts.prompt_loader import load_prompt


def _mark_design_complete(tool_context: ToolContext) -> str:
    """Mark design interview complete and transition to closing.

    Returns:
        Confirmation message
    """
    tool_context.state["interview_phase"] = "closing"
    return "Design interview complete. Moving to closing."


def _build_company_tool(company: str) -> AgentTool:
    """Build AgentTool for company-specific remote agent.

    Args:
        company: Company name (google, amazon, etc.)

    Returns:
        AgentTool wrapping RemoteA2aAgent

    Raises:
        ValueError: If no remote agent configured for company
    """
    agent_url = AgentProviderRegistry.get_agent_url(company, "system_design")

    if not agent_url:
        raise ValueError(
            f"No remote agent configured for {company} system_design. "
            f"Set {company.upper()}_AGENT_URL in environment."
        )

    remote_agent = RemoteA2aAgent(
        name=f"{company}_system_design_agent",
        description=f"{company.title()} system design expert",
        agent_card=f"{agent_url}{AGENT_CARD_WELL_KNOWN_PATH}",
    )

    return AgentTool(remote_agent, skip_summarization=True)


def _get_design_instruction(ctx: ReadonlyContext) -> str:
    """Get system design instruction with context."""
    routing = ctx.session.state.get("routing_decision", {})
    candidate_info = ctx.session.state.get("candidate_info", {})
    question = ctx.session.state.get("interview_question", "")

    return load_prompt(
        "system_design_agent.txt",
        company=routing.get("company", "COMPANY"),
        interview_type="system_design",
        candidate_name=candidate_info.get("name", "candidate"),
        interview_question=question,
    )


def build_design_agent(company: str) -> Agent:
    """Build system design interview agent with company-specific tools.

    Args:
        company: Company name (google, amazon, meta)

    Returns:
        Agent configured for system design interview

    Raises:
        ValueError: If company not configured
    """
    company_tool = _build_company_tool(company)

    return Agent(
        name="system_design_agent",
        model=os.getenv("AGENT_MODEL", "gemini-2.0-flash-exp"),
        description=f"Conducts {company.title()} system design interview",
        instruction=_get_design_instruction,
        tools=[company_tool, _mark_design_complete],
    )
