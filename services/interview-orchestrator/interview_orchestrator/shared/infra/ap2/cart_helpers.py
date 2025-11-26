"""AP2 Cart Helpers - Get cart mandates from merchant agents."""

import logging

from ap2.types.mandate import CART_MANDATE_DATA_KEY

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
        cart_mandate = response.get(CART_MANDATE_DATA_KEY)
        if not cart_mandate:
            logger.error(f"❌ Remote agent did not return {CART_MANDATE_DATA_KEY}")
            return None, f"Error: Remote agent did not return {CART_MANDATE_DATA_KEY}"

        # Extract price from AP2 structure
        cart_contents = cart_mandate.get("contents", {})
        payment_request = cart_contents.get("payment_request", {})
        details = payment_request.get("details", {})
        total = details.get("total", {})
        price = total.get("amount", {}).get("value", 0.0)

        logger.info(f"✅ Cart received: ${price:.2f} for {company} {interview_type}")
        return cart_mandate, None

    except Exception as e:
        logger.error(f"❌ Failed to get cart from {agent_url}: {e}")
        return None, f"Error: Failed to get pricing from {company} agent"
