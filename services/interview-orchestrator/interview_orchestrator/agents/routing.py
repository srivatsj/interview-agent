"""Routing agent for company and interview type selection."""

import asyncio
import json
import logging
import uuid

from google.adk.agents import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools import ToolContext

from ..shared.constants import get_gemini_model
from ..shared.infra.a2a.agent_registry import AgentProviderRegistry
from ..shared.infra.ap2.cart_helpers import get_cart_mandate
from ..shared.infra.ap2.payment_flow import process_payment
from ..shared.prompts.prompt_loader import load_prompt
from ..shared.schemas.routing_decision import RoutingDecision
from ..shared.session_store import active_sessions

logger = logging.getLogger(__name__)


async def confirm_company_selection(
    company: str,
    interview_type: str,
    tool_context: ToolContext,
) -> str:
    """Get pricing from remote agent and request user payment approval.

    Flow: validate → get cart → show confirmation → wait → create payment mandate

    Args:
        company: Company name (google, meta)
        interview_type: Interview type (system_design, coding, behavioral)
        tool_context: Tool execution context

    Returns:
        Approval/decline message after user responds (blocks until response or timeout)
    """
    # Prevent duplicate payment attempts
    if tool_context.state.get("payment_completed"):
        logger.warning("⚠️ Payment already completed, ignoring duplicate call")
        return "INTERNAL: Payment already completed. Do not call this tool again."

    # Validate company/interview_type combination
    if not AgentProviderRegistry.is_valid_combination(company, interview_type):
        available = AgentProviderRegistry.get_formatted_options()
        return f"Error: '{company} {interview_type}' not available.\n\nAvailable:\n{available}"

    # Get agent URL
    agent_url = AgentProviderRegistry.get_agent_url(company, interview_type)
    if not agent_url:
        return f"Error: No agent URL configured for {company}"

    # Call remote agent to create cart with pricing
    cart_mandate, error = await get_cart_mandate(agent_url, company, interview_type)
    if error:
        return error

    # Extract price from AP2 structure
    cart_contents = cart_mandate.get("contents", {})
    payment_request = cart_contents.get("payment_request", {})
    details = payment_request.get("details", {})
    total = details.get("total", {})
    price = total.get("amount", {}).get("value", 0.0)

    # Setup confirmation flow
    confirmation_id = str(uuid.uuid4())
    response_event = asyncio.Event()
    response_data = {"approved": None}

    logger.info(f"🔐 Setting up payment confirmation (id: {confirmation_id[:8]}...)")

    # Store response event in session (not serializable)
    session = tool_context.session
    if not hasattr(session, "_pending_confirmations"):
        session._pending_confirmations = {}
    session._pending_confirmations[confirmation_id] = {
        "event": response_event,
        "response": response_data,
    }

    # Notify frontend via WebSocket
    session_key = tool_context.state.get("session_key")
    logger.info(f"📡 Notifying frontend via WebSocket (session_key: {session_key})")

    websocket = active_sessions.get(session_key, {}).get("websocket") if session_key else None
    if not session_key or not websocket:
        logger.error(f"❌ WebSocket not available for session {session_key}")
        return "Error: WebSocket connection not found. Please refresh and try again."

    try:
        # Create confirmation data (local variable, not in state)
        confirmation_data = {
            "id": confirmation_id,
            "company": company.lower(),
            "interview_type": interview_type.lower(),
            "price": price,
            "cart_mandate": cart_mandate,
        }

        await websocket.send_text(
            json.dumps(
                {
                    "type": "state_update",
                    "state": {"pending_confirmation": confirmation_data},
                }
            )
        )
        logger.info("✅ Payment confirmation sent to frontend")
    except Exception as e:
        logger.error(f"❌ Failed to send WebSocket notification: {e}")
        return "Error: Failed to send payment confirmation. Please try again."

    # Wait for user response (blocks for up to 60 seconds)
    logger.info("⏳ Waiting for user response (timeout: 60s)...")
    try:
        await asyncio.wait_for(response_event.wait(), timeout=60.0)
        logger.info("✅ User responded to payment confirmation")
    except asyncio.TimeoutError:
        logger.warning("⏰ Payment confirmation timed out after 60 seconds")
        _cleanup_confirmation(tool_context, session, confirmation_id)
        return (
            "PAYMENT_TIMEOUT: User did not respond to payment confirmation in time. "
            "Ask if they want to try again or choose a different option."
        )

    # Get user decision
    approved = response_data.get("approved", False)
    logger.info(f"📋 User decision: {'APPROVED' if approved else 'DECLINED'}")
    _cleanup_confirmation(tool_context, session, confirmation_id)

    if not approved:
        logger.info("❌ Payment declined by user")
        return (
            f"PAYMENT_DECLINED: User canceled payment for "
            f"{company.title()} {interview_type.replace('_', ' ')} interview. "
            f"Ask if they want to try a different option or end the session."
        )

    # AP2 Flow: User approved, now process payment
    user_id = tool_context.state.get("user_id")
    interview_id = tool_context.state.get("interview_id")

    if not user_id:
        logger.error("❌ user_id not found in session state")
        return "Error: User not authenticated. Please refresh and try again."

    # Process payment via AP2 protocol
    payment_receipt, error = await process_payment(
        cart_mandate=cart_mandate,
        user_id=user_id,
        interview_id=interview_id,
        agent_url=agent_url,
        company=company,
    )
    if error:
        logger.error(f"💳 Payment processing failed: {error}")
        return (
            f"PAYMENT_FAILED: {error} "
            f"Ask user if they want to retry or choose a different option."
        )

    # Store payment proof and routing decision
    tool_context.state["payment_proof"] = payment_receipt
    tool_context.state["payment_completed"] = True
    tool_context.state["routing_decision"] = RoutingDecision(
        company=company.lower(),
        interview_type=interview_type.lower(),
        confidence=1.0,
    ).model_dump()
    tool_context.state["interview_phase"] = "intro"

    interview_name = f"{company.title()} {interview_type.replace('_', ' ')}"
    logger.info(f"✅ Payment proof stored! Starting {interview_name} interview")
    return (
        f"PAYMENT_SUCCESS: ${price:.2f} charged successfully. "
        f"{interview_name} interview is ready. "
        f"Announce success to user and transfer to coordinator to begin interview."
    )


def _cleanup_confirmation(tool_context: ToolContext, session, confirmation_id: str) -> None:
    """Clean up confirmation events."""
    if (
        hasattr(session, "_pending_confirmations")
        and confirmation_id in session._pending_confirmations
    ):
        del session._pending_confirmations[confirmation_id]


def get_routing_instruction(ctx: ReadonlyContext) -> str:
    """Get routing instruction with available options."""
    instruction = load_prompt(
        "routing_agent.txt",
        available_options=AgentProviderRegistry.get_formatted_options(),
    )
    return instruction


routing_agent = Agent(
    name="routing_agent",
    model=get_gemini_model(),
    description="Helps user choose company and interview type",
    instruction=get_routing_instruction,
    tools=[confirm_company_selection],
)
