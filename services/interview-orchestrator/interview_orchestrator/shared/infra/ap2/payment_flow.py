"""AP2 Payment Flow - Complete payment processing orchestration."""

import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timezone

import httpx

from ...infra.a2a.remote_client import call_remote_skill

logger = logging.getLogger(__name__)

# Frontend URL (Credentials Provider)
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")


async def process_payment(
    cart_mandate: dict,
    user_id: str,
    interview_id: str,
    agent_url: str,
    company: str,
) -> tuple[dict | None, str | None]:
    """Process complete AP2 payment flow.

    Flow: Get token → Create mandate → Charge via merchant → Return receipt

    Args:
        cart_mandate: Cart mandate from merchant
        user_id: User ID
        interview_id: Interview ID
        agent_url: Merchant agent URL
        company: Company name (for logging)

    Returns:
        Tuple of (payment_receipt, error_message)
        - If successful: (payment_receipt_dict, None)
        - If failed: (None, error_message)
    """
    try:
        # Step 1: Get payment token from Frontend (Credentials Provider)
        logger.info(f"🔐 Requesting payment token for user: {user_id}")
        payment_token = await _get_payment_token(user_id, cart_mandate)

        # Step 2: Create PaymentMandate
        logger.info("📝 Creating payment mandate...")
        payment_mandate = _create_payment_mandate(
            cart_mandate, payment_token, user_id, interview_id
        )

        # Step 3: Send PaymentMandate to merchant agent for charging
        logger.info(f"💳 Sending payment mandate to {company} agent...")
        payment_receipt = await _charge_via_merchant(agent_url, payment_mandate)

        # Step 4: Validate payment status
        if payment_receipt.get("payment_status", {}).get("status") != "success":
            error = payment_receipt.get("payment_status", {}).get("error", "Unknown error")
            logger.error(f"❌ Payment failed: {error}")
            return None, f"Payment failed: {error}"

        logger.info(f"✅ Payment successful: {payment_receipt['payment_id']}")
        return payment_receipt, None

    except Exception as e:
        logger.error(f"❌ Payment processing error: {e}")
        return None, f"Payment failed: {str(e)}. Please try again."


async def _get_payment_token(user_id: str, cart_mandate: dict) -> dict:
    """Get payment token from Frontend (Credentials Provider).

    Args:
        user_id: User ID
        cart_mandate: Cart mandate from merchant

    Returns:
        Payment token with encrypted payment method reference
    """
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{FRONTEND_URL}/api/payments/get-token",
            json={"user_id": user_id, "cart_mandate": cart_mandate},
            timeout=10.0,
        )
        response.raise_for_status()
        return response.json()["token"]


def _create_payment_mandate(
    cart_mandate: dict, payment_token: dict, user_id: str, interview_id: str
) -> dict:
    """Create PaymentMandate with cart hash and payment token.

    Args:
        cart_mandate: Cart mandate from merchant
        payment_token: Payment token from Credentials Provider
        user_id: User ID
        interview_id: Interview ID

    Returns:
        Payment mandate with cart hash and payment details
    """
    # Create hash from cart (excluding timestamp for consistency)
    cart_data = {
        "id": cart_mandate["id"],
        "total_amount": cart_mandate["total_amount"],
        "display_items": cart_mandate["display_items"],
    }
    cart_hash = hashlib.sha256(
        json.dumps(cart_data, sort_keys=True).encode()
    ).hexdigest()

    return {
        "payment_mandate_id": str(uuid.uuid4()),
        "cart_mandate_id": cart_mandate["id"],
        "cart_mandate": cart_mandate,  # Include full cart for transaction tracking
        "cart_hash": cart_hash,
        "payment_details_total": cart_mandate["total_amount"],
        "merchant_agent": cart_mandate.get("merchant_agent", "unknown"),
        "payment_response": {
            "method_name": "CARD",
            "details": {
                "token": payment_token,
                "user_id": user_id,
                "interview_id": interview_id,
            },
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


async def _charge_via_merchant(agent_url: str, payment_mandate: dict) -> dict:
    """Send PaymentMandate to merchant agent for charging.

    Args:
        agent_url: Merchant agent URL
        payment_mandate: Payment mandate with cart hash and payment token

    Returns:
        Payment receipt from merchant
    """
    response = await call_remote_skill(
        agent_url=agent_url,
        text="Process payment",
        data={"payment_mandate": payment_mandate},
    )
    return response.get("payment_receipt", {})
