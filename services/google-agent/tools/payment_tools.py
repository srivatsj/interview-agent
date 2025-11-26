"""Payment processing tools - AP2 compliant deterministic flow."""

import hashlib
import json
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone

import httpx
import jwt
from a2a.server.tasks import TaskUpdater
from a2a.types import DataPart, Part, Task, TextPart
from ap2.types.mandate import (
    CART_MANDATE_DATA_KEY,
    PAYMENT_MANDATE_DATA_KEY,
    CartContents,
    CartMandate,
)
from ap2.types.payment_receipt import PAYMENT_RECEIPT_DATA_KEY
from ap2.types.payment_request import (
    PaymentCurrencyAmount,
    PaymentDetailsInit,
    PaymentItem,
    PaymentMethodData,
    PaymentRequest,
)

from utils import find_data_part

logger = logging.getLogger(__name__)

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000")
MERCHANT_SECRET = os.getenv("MERCHANT_SECRET", "dev-secret-key-change-in-prod")

# Pricing configuration
PRICING = {
    "system_design": 3.00,
    "coding": 4.00,
    "behavioral": 2.50,
}


async def create_cart_for_interview(
    data_parts: list[dict],
    updater: TaskUpdater,
    current_task: Task | None,
) -> None:
    """Create AP2 compliant cart mandate for Google interview purchase.

    Deterministic tool - no LLM involved.
    """
    interview_type = find_data_part("interview_type", data_parts)

    if not interview_type:
        await updater.failed(
            message=updater.new_agent_message(
                parts=[Part(root=TextPart(text="Missing interview_type"))]
            )
        )
        return

    price = PRICING.get(interview_type.lower(), 3.00)
    cart_id = f"cart_google_{interview_type}_{uuid.uuid4().hex[:8]}"

    # Create AP2 compliant cart
    cart_contents = CartContents(
        id=cart_id,
        user_cart_confirmation_required=True,
        payment_request=PaymentRequest(
            method_data=[PaymentMethodData(supported_methods="card")],
            details=PaymentDetailsInit(
                id=cart_id,
                total=PaymentItem(
                    label="Total", amount=PaymentCurrencyAmount(currency="USD", value=price)
                ),
                display_items=[
                    PaymentItem(
                        label=f"Google {interview_type.replace('_', ' ').title()} Interview",
                        amount=PaymentCurrencyAmount(currency="USD", value=price),
                    )
                ],
            ),
        ),
        cart_expiry=(datetime.now(timezone.utc) + timedelta(minutes=15)).isoformat(),
        merchant_name="Google Interview Platform",
    )

    # Sign cart with JWT
    cart_signature = _sign_cart(cart_contents)

    cart_mandate = CartMandate(contents=cart_contents, merchant_authorization=cart_signature)

    logger.info(f"✅ Created AP2 cart: {cart_id} for ${price}")

    await updater.add_artifact(
        [Part(root=DataPart(data={CART_MANDATE_DATA_KEY: cart_mandate.model_dump()}))]
    )
    await updater.complete()


def _sign_cart(cart_contents: CartContents) -> str:
    """Sign cart contents with JWT.

    Minimal implementation - in production use proper RSA keys.
    """
    # Create hash of cart contents
    cart_dict = cart_contents.model_dump()
    cart_json = json.dumps(cart_dict, sort_keys=True)
    cart_hash = hashlib.sha256(cart_json.encode()).hexdigest()

    # Create JWT payload
    payload = {
        "iss": "google_interview_platform",
        "sub": "merchant",
        "cart_hash": cart_hash,
        "iat": datetime.now(timezone.utc).timestamp(),
        "exp": (datetime.now(timezone.utc).timestamp() + 900),  # 15 min
    }

    # Sign with secret (in production, use RSA private key)
    token = jwt.encode(payload, MERCHANT_SECRET, algorithm="HS256")
    return token


async def process_payment(
    data_parts: list[dict],
    updater: TaskUpdater,
    current_task: Task | None,
) -> None:
    """Process AP2 payment mandate via Frontend (Credentials Provider).

    Deterministic tool - no LLM involved.
    """
    payment_mandate = find_data_part(PAYMENT_MANDATE_DATA_KEY, data_parts)

    if not payment_mandate:
        await updater.failed(
            message=updater.new_agent_message(
                parts=[Part(root=TextPart(text="Missing payment_mandate"))]
            )
        )
        return

    # Extract from AP2 structure
    mandate_contents = payment_mandate.get("payment_mandate_contents", payment_mandate)
    mandate_id = mandate_contents.get("payment_mandate_id", "unknown")
    logger.info(f"💳 Processing AP2 payment: {mandate_id}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{FRONTEND_URL}/api/payments/execute",
                json={"payment_mandate": payment_mandate},
                timeout=30.0,
            )
            response.raise_for_status()
            result = response.json()

        payment_receipt = result.get("payment_receipt", {})
        payment_id = payment_receipt.get("payment_id", "unknown")
        logger.info(f"✅ Payment successful: {payment_id}")

        await updater.add_artifact(
            [Part(root=DataPart(data={PAYMENT_RECEIPT_DATA_KEY: payment_receipt}))]
        )
        await updater.complete()

    except httpx.HTTPStatusError as e:
        logger.error(f"❌ Payment failed: {e.response.status_code}")
        error_receipt = {
            "payment_id": "",
            "payment_status": {
                "status": "failed",
                "error": f"Payment processing failed: {e.response.text}",
            },
        }
        await updater.add_artifact(
            [Part(root=DataPart(data={PAYMENT_RECEIPT_DATA_KEY: error_receipt}))]
        )
        await updater.complete()

    except Exception as e:
        logger.error(f"❌ Payment error: {e}")
        error_receipt = {
            "payment_id": "",
            "payment_status": {
                "status": "failed",
                "error": str(e),
            },
        }
        await updater.add_artifact(
            [Part(root=DataPart(data={PAYMENT_RECEIPT_DATA_KEY: error_receipt}))]
        )
        await updater.complete()
