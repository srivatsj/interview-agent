"""Client to agent message handling."""

import base64
import json
import logging

from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect
from google.adk.agents import LiveRequestQueue
from google.genai.types import Blob, Content, Part

logger = logging.getLogger(__name__)


async def client_to_agent_messaging(
    websocket: WebSocket,
    live_request_queue: LiveRequestQueue,
    session_key: str,
    active_sessions: dict,
):
    """Relay client messages to the ADK agent.

    Args:
        websocket: WebSocket connection to client
        live_request_queue: Queue to send messages to agent
        session_key: Session identifier
        active_sessions: Dict of active sessions
    """
    try:
        while True:
            message_json = await websocket.receive_text()
            message = json.loads(message_json)
            mime_type = message["mime_type"]
            data = message["data"]

            # Check if this is a confirmation response from UI
            if mime_type == "confirmation_response":
                # Special message type for payment confirmation
                # Format: {"confirmation_id": "...", "approved": true/false}
                try:
                    confirmation_data = json.loads(data) if isinstance(data, str) else data
                    confirmation_id = confirmation_data.get("confirmation_id")
                    approved = confirmation_data.get("approved", False)

                    # Find the pending confirmation in session
                    if session_key in active_sessions:
                        session = active_sessions[session_key]["session"]

                        # Access tool context's pending confirmations
                        if hasattr(session, "_pending_confirmations"):
                            if confirmation_id in session._pending_confirmations:
                                pending = session._pending_confirmations[confirmation_id]

                                # Set the response data
                                pending["response"]["approved"] = approved

                                # Trigger the event to wake up the blocked tool
                                pending["event"].set()
                            else:
                                logger.warning(
                                    f"Confirmation ID {confirmation_id} not found in pending"
                                )
                        else:
                            logger.warning(
                                "No _pending_confirmations attribute on session"
                            )
                    else:
                        logger.warning(f"Session {session_key} not found in active sessions")

                except Exception as e:
                    logger.error(f"❌ Error processing confirmation response: {e}")

                continue

            if mime_type == "text/plain":
                # Send text message to agent
                content = Content(role="user", parts=[Part.from_text(text=data)])
                live_request_queue.send_content(content=content)
            elif mime_type in ["audio/pcm", "audio/webm"]:
                decoded_data = base64.b64decode(data)
                live_request_queue.send_realtime(Blob(data=decoded_data, mime_type=mime_type))
            elif mime_type == "image/png":
                decoded_data = base64.b64decode(data)
                content = Content(
                    role="user",
                    parts=[Part(inline_data=Blob(data=decoded_data, mime_type=mime_type))],
                )
                live_request_queue.send_content(content=content)
            else:
                raise ValueError(f"Mime type not supported: {mime_type}")

    except WebSocketDisconnect:
        logger.info("Client disconnected from WebSocket")
    except Exception as e:
        logger.error(f"❌ Error in client_to_agent_messaging: {e}")
        if logger.isEnabledFor(logging.DEBUG):
            logger.exception("Full traceback:")
