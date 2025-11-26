"""Coding interview agent."""

import logging

from ap2.types.payment_receipt import PAYMENT_RECEIPT_DATA_KEY
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

    Includes payment verification on first call to remote session.

    Args:
        query: Coding question or solution to get feedback on
        tool_context: Tool execution context

    Returns:
        Expert feedback from remote agent
    """
    routing = tool_context.state.get("routing_decision", {})
    company = routing.get("company")

    if not company:
        return "No company selected. Cannot access remote expert."

    agent_url = AgentProviderRegistry.get_agent_url(company, "coding")
    if not agent_url:
        return f"Remote expert not available for {company}."

    try:
        # Get session info for multi-turn conversation
        interview_id = tool_context.state.get("interview_id", tool_context.invocation_id)
        user_id = tool_context.state.get("user_id", "unknown")

        logger.info(
            f"🔗 Calling remote expert at {agent_url} for session {interview_id[:8] if isinstance(interview_id, str) else interview_id}"
        )
        logger.info(f"📝 Query: {query[:100]}...")

        # Build data payload
        data_payload = {
            "message": query,
            "user_id": user_id,
            "session_id": interview_id,
        }

        # Always include payment proof - remote agent decides whether to use it
        payment_proof = tool_context.state.get("payment_proof")
        if payment_proof:
            data_payload[PAYMENT_RECEIPT_DATA_KEY] = payment_proof
            logger.info("📋 Including payment receipt in remote call")

        # Include latest canvas screenshot if available
        # Canvas is always sent as image (screenshot) whether it contains diagrams or code
        canvas_screenshot = tool_context.state.get("canvas_screenshot")
        if canvas_screenshot:
            data_payload["canvas_screenshot"] = canvas_screenshot
            logger.info("📷 Including canvas screenshot in remote call")

        # Call remote agent with conversation context
        response = await call_remote_skill(
            agent_url=agent_url,
            text="Conduct interview",
            data=data_payload,
        )

        logger.info(
            f"✅ Got response from remote expert ({len(response.get('message', ''))} chars)"
        )

        return response.get("message", "")

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
