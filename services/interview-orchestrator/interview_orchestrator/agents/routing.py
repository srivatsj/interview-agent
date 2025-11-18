"""Routing agent for company and interview type selection."""

import asyncio
import json
import logging
import uuid

from google.adk.agents import Agent
from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.tools import ToolContext

from ..shared.agent_registry import AgentProviderRegistry
from ..shared.constants import get_gemini_model
from ..shared.prompts.prompt_loader import load_prompt
from ..shared.schemas.routing_decision import RoutingDecision
from ..shared.session_store import active_sessions

logger = logging.getLogger(__name__)


async def confirm_company_selection(
    company: str,
    interview_type: str,
    tool_context: ToolContext,
) -> str:
    """Request payment approval and BLOCK until user responds.

    This tool will pause the agent until the user approves or declines payment.
    Times out after 60 seconds if no response.

    Args:
        company: The company (google, meta, etc.)
        interview_type: The interview type (system_design, coding, or behavioral)
        tool_context: Tool execution context

    Returns:
        Success or decline message after user responds
    """
    # Check if payment already processed
    existing_decision = tool_context.state.get("routing_decision")
    if existing_decision:
        if (existing_decision.get("company") == company.lower() and
            existing_decision.get("interview_type") == interview_type.lower()):
            return f"Payment already confirmed for {company} {interview_type}. Ready to proceed."

    # Validate combination (allow free_practice without registry check)
    is_free = company.lower() == "free_practice"
    is_valid = AgentProviderRegistry.is_valid_combination(company, interview_type)
    if not is_free and not is_valid:
        available = AgentProviderRegistry.get_formatted_options()
        return (
            f"Error: '{company} {interview_type}' is not available.\n\n"
            f"Available options:\n{available}"
        )

    # Pricing
    pricing = {"google": 3.00, "meta": 2.00, "free_practice": 0.00}
    price = pricing.get(company.lower(), 0.00)

    # Generate unique confirmation ID
    confirmation_id = str(uuid.uuid4())

    # Create event and response storage
    response_event = asyncio.Event()
    response_data = {"approved": None}

    # Store confirmation in state for frontend (serializable)
    tool_context.state["pending_confirmation"] = {
        "id": confirmation_id,
        "company": company.lower(),
        "interview_type": interview_type.lower(),
        "price": price,
    }

    # Store event in session memory (not serializable, can't go in state)
    # Access session from tool_context and store there
    # This allows client_to_agent to find it via active_sessions
    session = tool_context.session
    if not hasattr(session, "_pending_confirmations"):
        session._pending_confirmations = {}

    session._pending_confirmations[confirmation_id] = {
        "event": response_event,
        "response": response_data,
    }

    # Send notification to frontend BEFORE blocking
    # Get session_key and websocket from active_sessions
    session_key = tool_context.state.get("session_key")
    if session_key and session_key in active_sessions:
        websocket = active_sessions[session_key].get("websocket")
        if websocket:
            # Send state notification message
            notification = {
                "type": "state_update",
                "state": {
                    "pending_confirmation": tool_context.state["pending_confirmation"]
                }
            }
            try:
                await websocket.send_text(json.dumps(notification))
            except Exception as e:
                logger.warning(f"Failed to send notification to frontend: {e}")

    # BLOCK HERE - wait for user to respond via UI
    try:
        await asyncio.wait_for(response_event.wait(), timeout=60.0)
    except asyncio.TimeoutError:
        # Cleanup
        tool_context.state["pending_confirmation"] = None
        session = tool_context.session
        if (hasattr(session, "_pending_confirmations") and
            confirmation_id in session._pending_confirmations):
            del session._pending_confirmations[confirmation_id]

        return "Payment confirmation timed out after 60 seconds. Please try again."

    # User responded! Process the response
    approved = response_data.get("approved", False)

    # Cleanup
    tool_context.state["pending_confirmation"] = None
    session = tool_context.session
    if (hasattr(session, "_pending_confirmations") and
        confirmation_id in session._pending_confirmations):
        del session._pending_confirmations[confirmation_id]

    if approved:
        # Save routing decision and advance to intro
        routing_decision = RoutingDecision(
            company=company.lower(),
            interview_type=interview_type.lower(),
            confidence=1.0,
        )

        tool_context.state["routing_decision"] = routing_decision.model_dump()
        tool_context.state["interview_phase"] = "intro"
        tool_context.state["payment_confirmed"] = price > 0

        price_msg = f" Payment of ${price:.2f} confirmed." if price > 0 else ""
        return (
            f"Payment approved!{price_msg} "
            f"Ready to start {company.title()} {interview_type.replace('_', ' ')} interview."
        )
    else:
        return (
            f"Payment declined for {company.title()} {interview_type.replace('_', ' ')} interview. "
            "User can choose a different option."
        )


def set_routing_decision(
    company: str,
    interview_type: str,
    tool_context: ToolContext,
) -> str:
    """Save routing decision for free practice (no confirmation needed).

    Args:
        company: Should be "free_practice"
        interview_type: The interview type (system_design, coding, or behavioral)
        tool_context: Tool execution context

    Returns:
        Confirmation message or error if combination is invalid
    """
    # Only allow free_practice through this tool
    if company.lower() != "free_practice":
        return (
            f"Error: This tool is only for free practice. "
            f"Use confirm_company_selection for {company}."
        )

    routing_decision = RoutingDecision(
        company=company.lower(),
        interview_type=interview_type.lower(),
        confidence=1.0,
    )

    tool_context.state["routing_decision"] = routing_decision.model_dump()
    tool_context.state["interview_phase"] = "intro"

    logger.info(f"Routing decision saved: {company.lower()} {interview_type.lower()}")

    return (
        f"Routing saved: {company.lower()} {interview_type.lower()}. "
        "Starting interview intro phase."
    )


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
    tools=[confirm_company_selection, set_routing_decision],
)
