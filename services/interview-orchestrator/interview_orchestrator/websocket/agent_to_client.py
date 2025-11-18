"""Agent to client message streaming."""

import base64
import json
import logging

from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect

logger = logging.getLogger(__name__)


async def agent_to_client_messaging(
    websocket: WebSocket, live_events, session_key: str, active_sessions: dict
):
    """Stream agent responses to the WebSocket client.

    Uses structured message format matching the working ADK sample.
    Each message contains all event data in a single structured object.

    Args:
        websocket: WebSocket connection to client
        live_events: Async generator of events from agent
        session_key: Session identifier to lookup session state
        active_sessions: Dict of active sessions with state
    """
    try:
        event_count = 0
        async for event in live_events:
            event_count += 1
            if event_count % 50 == 0:  # Log every 50th event to track progress
                logger.debug(f"Processed {event_count} events from agent")

            # Get current session state
            session_state = {}
            if session_key in active_sessions:
                session = active_sessions[session_key]["session"]
                session_state = dict(session.state) if session.state else {}

            # Create structured message matching working ADK sample format
            message_to_send = {
                "author": event.author or "agent",
                "is_partial": event.partial or False,
                "turn_complete": event.turn_complete or False,
                "interrupted": event.interrupted or False,
                "parts": [],
                "input_transcription": None,
                "output_transcription": None,
                "state": session_state,  # Include session state for frontend
            }

            # If no content, send only turn events if present
            if not event.content:
                if message_to_send["turn_complete"] or message_to_send["interrupted"]:
                    await websocket.send_text(json.dumps(message_to_send))
                continue

            # Collect all text for transcription
            transcription_text = "".join(part.text for part in event.content.parts if part.text)

            # Handle user input transcription
            if hasattr(event.content, "role") and event.content.role == "user":
                if transcription_text:
                    message_to_send["input_transcription"] = {
                        "text": transcription_text,
                        "is_final": not event.partial,
                    }

            # Handle agent/model responses (role can be "model", "agent", or None)
            elif not (hasattr(event.content, "role") and event.content.role == "user"):
                # Add output transcription if available
                if transcription_text:
                    message_to_send["output_transcription"] = {
                        "text": transcription_text,
                        "is_final": not event.partial,
                    }
                    message_to_send["parts"].append({"type": "text", "data": transcription_text})

                # Process all parts
                for part in event.content.parts:
                    # Handle audio data
                    if part.inline_data and part.inline_data.mime_type.startswith("audio/pcm"):
                        audio_data = part.inline_data.data
                        encoded_audio = base64.b64encode(audio_data).decode("ascii")
                        message_to_send["parts"].append(
                            {"type": "audio/pcm", "data": encoded_audio}
                        )

                    # Handle function calls
                    elif part.function_call:
                        message_to_send["parts"].append(
                            {
                                "type": "function_call",
                                "data": {
                                    "id": part.function_call.id,
                                    "name": part.function_call.name,
                                    "args": part.function_call.args or {},
                                },
                            }
                        )

                    # Handle function responses
                    elif part.function_response:
                        message_to_send["parts"].append(
                            {
                                "type": "function_response",
                                "data": {
                                    "name": part.function_response.name,
                                    "response": part.function_response.response or {},
                                },
                            }
                        )

            # Send message if it has content or status changes
            if (
                message_to_send["parts"]
                or message_to_send["turn_complete"]
                or message_to_send["interrupted"]
                or message_to_send["input_transcription"]
                or message_to_send["output_transcription"]
            ):
                json_message = json.dumps(message_to_send)

                # Only log important events (skip routine audio/text to reduce noise)
                non_audio_parts = [p for p in message_to_send["parts"] if p["type"] != "audio/pcm"]
                has_important_event = (
                    any(p["type"] == "function_call" for p in non_audio_parts) or
                    message_to_send["turn_complete"] or
                    message_to_send["interrupted"]
                )

                if has_important_event:
                    tc = message_to_send['turn_complete']
                    intr = message_to_send['interrupted']
                    logger.info(f"📤 Event: turn_complete={tc}, interrupted={intr}")

                # Log when sending payment confirmation state to frontend
                if session_state.get("pending_confirmation"):
                    logger.info(
                        f"💳 Sending pending_confirmation to frontend: "
                        f"{session_state['pending_confirmation']}"
                    )

                await websocket.send_text(json_message)

    except WebSocketDisconnect:
        logger.info("Client disconnected from WebSocket")
    except Exception as e:
        logger.error(f"❌ Error in agent_to_client_messaging: {e}")
        # Don't log full stack trace unless debug mode
        if logger.isEnabledFor(logging.DEBUG):
            logger.exception("Full traceback:")
