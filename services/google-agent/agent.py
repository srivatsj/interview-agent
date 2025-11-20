"""Google System Design Interview Agent - Exposed via A2A Protocol

Conducts Google-style system design interviews with premium feedback.
Exposes cart creation for AP2 payment protocol.
"""

import json
import logging
import os
import uuid
from datetime import datetime, timezone

import httpx
from a2a.types import AgentCard, AgentSkill
from dotenv import load_dotenv
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.agents import Agent
from google.adk.tools import ToolContext

load_dotenv()

logger = logging.getLogger(__name__)

# Frontend URL (Credentials Provider)
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


# Cart creation skill for AP2 payment protocol
def create_cart_for_interview(interview_type: str, tool_context: ToolContext) -> str:
    """Create cart mandate for Google interview purchase.

    Args:
        interview_type: Type of interview (system_design, coding, behavioral)
        tool_context: ADK tool context

    Returns:
        JSON string with cart_mandate
    """

    # Google interview pricing
    PRICING = {
        "system_design": 3.00,
        "coding": 4.00,
        "behavioral": 2.50,
    }

    price = PRICING.get(interview_type.lower(), 3.00)
    cart_id = f"cart_google_{interview_type}_{uuid.uuid4().hex[:8]}"

    # Create CartMandate (simplified for Phase 1 - no actual AP2 types yet)
    cart_mandate = {
        "id": cart_id,
        "merchant_agent": "google_design_agent",
        "interview_type": interview_type,  # Include for transaction tracking
        "total_amount": {"currency": "USD", "value": price},
        "display_items": [
            {
                "label": f"Google {interview_type.replace('_', ' ').title()} Interview",
                "amount": {"currency": "USD", "value": price},
            }
        ],
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    # Return as JSON string (ADK will send this as text over A2A)
    return json.dumps({"cart_mandate": cart_mandate}, indent=2)


async def process_payment(payment_mandate: dict, tool_context: ToolContext) -> str:
    """Process payment via Frontend (Credentials Provider).

    This is the merchant side of the AP2 payment flow. Receives PaymentMandate
    from Shopping Agent, forwards to Credentials Provider for charging.

    Args:
        payment_mandate: Payment mandate with cart hash and payment token
        tool_context: ADK tool context

    Returns:
        JSON string with payment_receipt
    """
    mandate_id = payment_mandate.get("payment_mandate_id", "unknown")
    logger.info(f"💳 Processing payment mandate: {mandate_id}")

    try:
        # Call Frontend (Credentials Provider) to execute payment
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{FRONTEND_URL}/api/payments/execute",
                json={"payment_mandate": payment_mandate},
                timeout=30.0,
            )
            response.raise_for_status()
            result = response.json()

        payment_receipt = result.get("payment_receipt", {})
        logger.info(f"✅ Payment processed: {payment_receipt.get('payment_id', 'unknown')}")

        return json.dumps({"payment_receipt": payment_receipt}, indent=2)

    except httpx.HTTPStatusError as e:
        logger.error(f"❌ Payment failed with status {e.response.status_code}: {e.response.text}")
        return json.dumps({
            "payment_receipt": {
                "payment_id": "",
                "payment_status": {
                    "status": "failed",
                    "error": f"Payment processing failed: {e.response.text}",
                },
            }
        }, indent=2)
    except Exception as e:
        logger.error(f"❌ Payment processing error: {e}")
        return json.dumps({
            "payment_receipt": {
                "payment_id": "",
                "payment_status": {
                    "status": "failed",
                    "error": f"Payment processing error: {str(e)}",
                },
            }
        }, indent=2)


# System design interview agent
root_agent = Agent(
    name="google_system_design_agent",
    model=os.getenv("AGENT_MODEL", "gemini-2.0-flash-exp"),
    description="Google-style system design interviewer with premium feedback",
    instruction="""You are a senior Google engineer conducting a system design interview.

Focus areas:
- Scale: billions of users, QPS calculations, data volume estimation
- Distributed systems: consistency, replication, sharding, CAP theorem
- Google-specific: Spanner, Bigtable, MapReduce patterns
- Production: monitoring, reliability, disaster recovery

Be thorough but conversational. Ask clarifying questions.
Guide the candidate through trade-offs.""",
    tools=[create_cart_for_interview, process_payment],
)

# Agent card with cart creation skill
agent_card = AgentCard(
    name="google_system_design_agent",
    url="http://localhost:8001",
    description="Google system design interview expert with premium feedback",
    version="1.0.0",
    capabilities={},
    skills=[
        AgentSkill(
            id="create_cart_for_interview",
            name="Create Interview Cart",
            description="Creates cart mandate with pricing for Google interview purchase",
            tags=["payment", "cart", "interview"],
        ),
        AgentSkill(
            id="process_payment",
            name="Process Payment",
            description="Processes payment mandate via Credentials Provider",
            tags=["payment", "ap2", "stripe"],
        ),
    ],
    defaultInputModes=["text/plain"],
    defaultOutputModes=["application/json"],
    supportsAuthenticatedExtendedCard=False,
)

# Expose via A2A protocol
a2a_app = to_a2a(root_agent, port=8001, agent_card=agent_card)
