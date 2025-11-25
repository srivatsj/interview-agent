"""System design interview agent."""

import logging

from google.adk.agents import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools import ToolContext

from ...shared.constants import get_gemini_model
from ...shared.infra.a2a.agent_registry import AgentProviderRegistry
from ...shared.infra.a2a.remote_client import call_remote_skill
from ...shared.prompts.prompt_loader import load_prompt

logger = logging.getLogger(__name__)


async def ask_remote_expert(query: str, tool_context: ToolContext) -> str:
    """Get feedback from company-specific remote expert agent.

    Updated to work with new Google agent custom executor pattern.
    Maintains conversation state via context_id for multi-turn.

    Args:
        query: Question or design problem to get feedback on
        tool_context: Tool execution context

    Returns:
        Expert feedback from remote agent
    """
    routing = tool_context.state.get("routing_decision", {})
    company = routing.get("company")

    if not company:
        return "No company selected. Cannot access remote expert."

    agent_url = AgentProviderRegistry.get_agent_url(company, "system_design")
    if not agent_url:
        return f"Remote expert not available for {company}."

    try:
        # Get session info for multi-turn conversation
        interview_id = tool_context.state.get("interview_id", tool_context.invocation_id)
        user_id = tool_context.state.get("user_id", "unknown")

        logger.info(f"🔗 Calling remote expert at {agent_url} for session {interview_id[:8] if isinstance(interview_id, str) else interview_id}")
        logger.info(f"📝 Query: {query[:100]}...")

        # Build data payload
        data_payload = {
            "message": query,
            "user_id": user_id,
            "session_id": interview_id,
        }

        # Include latest canvas screenshot if available
        # Frontend sends updates every 30-60s, we always send latest to remote expert
        canvas_screenshot = tool_context.state.get("canvas_screenshot")
        if canvas_screenshot:
            data_payload["canvas_screenshot"] = canvas_screenshot
            logger.info("📷 Including latest canvas screenshot in remote call")

        # Call remote agent with conversation context + latest canvas
        response = await call_remote_skill(
            agent_url=agent_url,
            text="Conduct interview",
            data=data_payload,
        )

        logger.info(f"✅ Got response from remote expert ({len(response.get('message', ''))} chars)")

        return response.get("message", "")

    except Exception as e:
        logger.error(f"Failed to call remote expert at {agent_url}: {e}")
        return f"Error contacting {company} expert. Continuing with general guidance."


def _mark_design_complete(tool_context: ToolContext) -> str:
    """Mark design interview complete and transition to closing."""
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
        ask_remote_expert,
        _mark_design_complete,
    ],
)
