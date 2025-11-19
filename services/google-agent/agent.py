"""Google System Design Interview Agent - Exposed via A2A Protocol

Conducts Google-style system design interviews with premium feedback.
Exposes cart creation for AP2 payment protocol.
"""

import json
import os
import uuid
from datetime import datetime, timezone

from a2a.types import AgentCard, AgentSkill
from dotenv import load_dotenv
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.agents import Agent
from google.adk.tools import ToolContext

load_dotenv()


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
    tools=[create_cart_for_interview],
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
    ],
    defaultInputModes=["text/plain"],
    defaultOutputModes=["application/json"],
    supportsAuthenticatedExtendedCard=False,
)

# Expose via A2A protocol
a2a_app = to_a2a(root_agent, port=8001, agent_card=agent_card)
