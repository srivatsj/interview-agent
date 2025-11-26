"""Interview conductor tools - ADK LLM-based flow."""

import logging
import os
from typing import Any

from a2a.server.tasks import TaskUpdater
from a2a.types import DataPart, Part, Task, TaskState, TextPart
from ap2.types.payment_receipt import PAYMENT_RECEIPT_DATA_KEY, PaymentReceipt, Success
from google.adk.agents import LlmAgent
from google.adk.sessions import InMemorySessionService
from google.genai import types as genai_types
from pydantic import ValidationError

from utils import find_data_part

logger = logging.getLogger(__name__)

# Session service for payment verification tracking
_session_service = InMemorySessionService()

# Interview agent
interview_agent = LlmAgent(
    name="google_interviewer",
    model=os.getenv("AGENT_MODEL", "gemini-2.0-flash-exp"),
    description="Google system design interviewer",
    instruction="""You are a senior Google engineer conducting a system design interview.

Focus areas:
- Scale: billions of users, QPS calculations, data volume
- Distributed systems: consistency, replication, sharding, CAP theorem
- Google tech: Spanner, Bigtable, MapReduce patterns
- Production: monitoring, reliability, disaster recovery

You will receive:
- Text messages from the candidate
- System design: Canvas screenshots (PNG images of whiteboard diagrams)
- Code: Text content (code implementations, no images)

When analyzing visual diagrams:
1. Acknowledge what you see in the architecture diagram
2. Provide specific feedback on component relationships and data flow
3. Ask probing questions about design decisions
4. Suggest improvements or point out potential issues

When analyzing code:
1. Review the implementation logic and structure
2. Comment on code quality, patterns, and best practices
3. Identify potential bugs or edge cases
4. Suggest optimizations

Interview flow:
1. Start with clarifying questions about requirements
2. Guide through high-level design
3. Deep dive into specific components
4. Discuss trade-offs and alternatives
5. End with questions and feedback

Be thorough but conversational. Ask probing questions.""",
)


async def conduct_interview(
    data_parts: list[dict],
    updater: TaskUpdater,
    current_task: Task | None,
) -> None:
    """Conduct system design interview using ADK LLM.

    Non-deterministic, conversational, multi-turn.
    Supports multimodal input:
    - System design: PNG screenshots (spatial diagrams)
    - Code: Text content (precise parsing)

    Security: Verifies payment once per session before allowing interview access.
    """
    user_message = find_data_part("message", data_parts)
    user_id = find_data_part("user_id", data_parts) or updater.context_id
    session_id = find_data_part("session_id", data_parts) or updater.context_id

    # Canvas data (always sent as screenshot/image, whether diagrams or code)
    canvas_screenshot = find_data_part("canvas_screenshot", data_parts)

    if not user_message:
        await updater.failed(
            message=updater.new_agent_message(parts=[Part(root=TextPart(text="Missing message"))])
        )
        return

    # --- Payment Verification (once per session) ---
    session = await _session_service.get_session(
        app_name="google_interview",
        user_id=user_id,
        session_id=session_id,
    )

    if session is None:
        # First call - create session and verify payment
        session = await _session_service.create_session(
            app_name="google_interview",
            user_id=user_id,
            session_id=session_id,
        )

    if not session.state.get("payment_verified"):
        # Verify payment receipt
        payment_receipt_data = find_data_part(PAYMENT_RECEIPT_DATA_KEY, data_parts)

        if not payment_receipt_data:
            logger.error(f"❌ Payment verification required for session {session_id[:8]}")
            await updater.failed(
                message=updater.new_agent_message(
                    parts=[
                        Part(
                            root=TextPart(text="Payment verification required to access interview")
                        )
                    ]
                )
            )
            return

        try:
            payment_receipt = PaymentReceipt.model_validate(payment_receipt_data)
        except ValidationError as e:
            logger.error(f"❌ Invalid payment receipt: {e}")
            await updater.failed(
                message=updater.new_agent_message(
                    parts=[Part(root=TextPart(text=f"Invalid payment receipt: {str(e)}"))]
                )
            )
            return

        # Check payment status is Success (not Error or Failure)
        if not isinstance(payment_receipt.payment_status, Success):
            logger.error(f"❌ Payment not successful for session {session_id[:8]}")
            await updater.failed(
                message=updater.new_agent_message(
                    parts=[
                        Part(
                            root=TextPart(
                                text="Payment not successful. Please complete payment first."
                            )
                        )
                    ]
                )
            )
            return

        # Store payment verification in session
        session.state["payment_verified"] = True
        session.state["payment_id"] = payment_receipt.payment_id
        session.state["payment_amount"] = payment_receipt.amount.value
        logger.info(
            f"✅ Payment verified for session {session_id[:8]} (payment_id: {payment_receipt.payment_id})"
        )

    else:
        logger.info(f"✅ Session {session_id[:8]} already payment-verified")

    logger.info(f"🎤 Interview turn for session {session_id[:8]}")
    if canvas_screenshot:
        logger.info(f"📷 Canvas screenshot included ({len(canvas_screenshot)} bytes)")

    try:
        # Build multimodal message parts
        message_parts = [genai_types.Part(text=user_message)]

        # Add canvas screenshot as inline image if provided
        if canvas_screenshot:
            try:
                import base64

                # Decode base64 to bytes
                image_bytes = base64.b64decode(canvas_screenshot)

                # Add image part (Gemini supports inline images)
                message_parts.append(
                    genai_types.Part(
                        inline_data=genai_types.Blob(mime_type="image/png", data=image_bytes)
                    )
                )
                logger.info("✅ Canvas screenshot decoded and added to message")
            except Exception as img_error:
                logger.warning(f"⚠️ Failed to decode canvas screenshot: {img_error}")
                # Continue without image - graceful degradation

        # Run agent with multimodal message
        events = []
        async for event in interview_agent.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=genai_types.Content(role="user", parts=message_parts),
        ):
            events.append(event)

        # Get final response
        if not events or not events[-1].message:
            raise ValueError("No response from interview agent")

        final_event = events[-1]
        response_text = _extract_text_from_content(final_event.message)

        logger.info(f"🎤 Interview response for {session_id[:8]}")

        # Always return message for multi-turn conversation
        await updater.add_artifact([Part(root=DataPart(data={"message": response_text}))])
        await updater.update_status(
            TaskState.input_required,
            updater.new_agent_message(parts=[Part(root=TextPart(text=response_text))]),
            final=True,
        )

    except Exception as e:
        logger.error(f"❌ Interview error: {e}", exc_info=True)
        await updater.failed(
            message=updater.new_agent_message(
                parts=[Part(root=TextPart(text=f"Interview error: {str(e)}"))]
            )
        )


def _extract_text_from_content(content: Any) -> str:
    """Extract text from GenAI Content object."""
    if not content or not hasattr(content, "parts"):
        return ""

    text_parts = []
    for part in content.parts:
        if hasattr(part, "text") and part.text:
            text_parts.append(part.text)

    return " ".join(text_parts)
