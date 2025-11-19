"""Routing agent for company and interview type selection."""

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone

from google.adk.agents import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools import ToolContext

from ..shared.constants import get_gemini_model
from ..shared.infra.a2a.agent_registry import AgentProviderRegistry
from ..shared.infra.a2a.remote_client import call_remote_skill
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
    # Validate company/interview_type combination
    if not AgentProviderRegistry.is_valid_combination(company, interview_type):
        available = AgentProviderRegistry.get_formatted_options()
        return f"Error: '{company} {interview_type}' not available.\n\nAvailable:\n{available}"

    # Get agent URL
    agent_url = AgentProviderRegistry.get_agent_url(company, interview_type)
    if not agent_url:
        return f"Error: No agent URL configured for {company}"

    # Call remote agent to create cart with pricing
    logger.info(f"💳 Requesting cart from {company} agent at {agent_url}")
    try:
        response = await call_remote_skill(
            agent_url=agent_url,
            text="Create cart for interview",
            data={"interview_type": interview_type},
        )
        cart_mandate = response.get("cart_mandate")
        if not cart_mandate:
            logger.error("❌ Remote agent did not return cart_mandate")
            return "Error: Remote agent did not return cart_mandate"

        price = cart_mandate["total_amount"]["value"]
        logger.info(f"✅ Cart received: ${price:.2f} for {company} {interview_type}")
    except Exception as e:
        logger.error(f"❌ Failed to get cart from {agent_url}: {e}")
        return f"Error: Failed to get pricing from {company} agent"

    # Setup confirmation flow
    confirmation_id = str(uuid.uuid4())
    response_event = asyncio.Event()
    response_data = {"approved": None}

    logger.info(f"🔐 Setting up payment confirmation (id: {confirmation_id[:8]}...)")

    # Store confirmation details for frontend
    tool_context.state["pending_confirmation"] = {
        "id": confirmation_id,
        "company": company.lower(),
        "interview_type": interview_type.lower(),
        "price": price,
        "cart_mandate": cart_mandate,
    }

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
    if session_key in active_sessions:
        websocket = active_sessions[session_key].get("websocket")
        if websocket:
            try:
                await websocket.send_text(
                    json.dumps(
                        {
                            "type": "state_update",
                            "state": {
                                "pending_confirmation": tool_context.state["pending_confirmation"]
                            },
                        }
                    )
                )
                logger.info("✅ Payment confirmation sent to frontend")
            except Exception as e:
                logger.warning(f"⚠️ Failed to send WebSocket notification: {e}")
        else:
            logger.warning(f"⚠️ No WebSocket found for session {session_key}")
    else:
        logger.warning(f"⚠️ Session key {session_key} not in active_sessions")

    # Wait for user response (blocks for up to 60 seconds)
    logger.info("⏳ Waiting for user response (timeout: 60s)...")
    try:
        await asyncio.wait_for(response_event.wait(), timeout=60.0)
        logger.info("✅ User responded to payment confirmation")
    except asyncio.TimeoutError:
        logger.warning("⏰ Payment confirmation timed out after 60 seconds")
        _cleanup_confirmation(tool_context, session, confirmation_id)
        return "Payment confirmation timed out. Please try again."

    # Get user decision
    approved = response_data.get("approved", False)
    logger.info(f"📋 User decision: {'APPROVED' if approved else 'DECLINED'}")
    _cleanup_confirmation(tool_context, session, confirmation_id)

    if not approved:
        logger.info("❌ Payment declined by user")
        return f"Payment declined for {company.title()} {interview_type.replace('_', ' ')}."

    # User approved - create PaymentMandate (Phase 1: fake token)
    logger.info("💰 Creating payment mandate...")
    payment_mandate = {
        "payment_mandate_id": str(uuid.uuid4()),
        "cart_mandate_id": cart_mandate["id"],
        "payment_details_total": cart_mandate["total_amount"],
        "merchant_agent": cart_mandate["merchant_agent"],
        "payment_response": {"method_name": "CARD", "details": {"token": "tok_fake_test_phase1"}},
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Save payment proof and routing decision
    tool_context.state["payment_proof"] = payment_mandate
    tool_context.state["routing_decision"] = RoutingDecision(
        company=company.lower(),
        interview_type=interview_type.lower(),
        confidence=1.0,
    ).model_dump()
    tool_context.state["interview_phase"] = "intro"
    tool_context.state["payment_completed"] = True

    interview_name = f"{company.title()} {interview_type.replace('_', ' ')}"
    logger.info(f"✅ Payment approved! Starting {interview_name} interview")
    return f"Payment approved (${price:.2f}). Starting {interview_name} interview."


def _cleanup_confirmation(tool_context: ToolContext, session, confirmation_id: str) -> None:
    """Clean up confirmation state and events."""
    tool_context.state["pending_confirmation"] = None
    if hasattr(session, "_pending_confirmations"):
        if confirmation_id in session._pending_confirmations:
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
