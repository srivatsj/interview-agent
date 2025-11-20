"""AP2 Cart Helpers - Get cart mandates from merchant agents."""

import logging

from ...infra.a2a.remote_client import call_remote_skill

logger = logging.getLogger(__name__)


async def get_cart_mandate(
    agent_url: str, company: str, interview_type: str
) -> tuple[dict | None, str | None]:
    """Get cart mandate from merchant agent.

    Args:
        agent_url: Merchant agent URL
        company: Company name (for logging)
        interview_type: Interview type

    Returns:
        Tuple of (cart_mandate, error_message)
        - If successful: (cart_mandate_dict, None)
        - If failed: (None, error_message)
    """
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
            return None, "Error: Remote agent did not return cart_mandate"

        price = cart_mandate["total_amount"]["value"]
        logger.info(f"✅ Cart received: ${price:.2f} for {company} {interview_type}")
        return cart_mandate, None

    except Exception as e:
        logger.error(f"❌ Failed to get cart from {agent_url}: {e}")
        return None, f"Error: Failed to get pricing from {company} agent"
