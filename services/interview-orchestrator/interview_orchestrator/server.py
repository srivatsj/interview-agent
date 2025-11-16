"""WebSocket Server for Interview Orchestrator.

FastAPI server enabling real-time bidirectional communication with ADK agent.
Uses BIDI streaming for user interruption support.
"""

import asyncio
import base64
import json
import logging
import os
from pathlib import Path

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.websockets import WebSocketDisconnect
from google.adk.agents import LiveRequestQueue
from google.adk.agents.run_config import RunConfig
from google.adk.runners import InMemoryRunner
from google.adk.sessions import DatabaseSessionService
from google.genai.types import Blob, Content, Part

from .root_agent import root_agent

# Load environment variables
load_dotenv()

# Configure logging - suppress verbose audio chunk logs
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Suppress noisy loggers completely
logging.getLogger("google_adk.google.adk.flows.llm_flows.audio_cache_manager").setLevel(
    logging.ERROR
)
logging.getLogger("google_adk.google.adk.models.gemini_llm_connection").setLevel(logging.ERROR)
logging.getLogger("google_adk.google.adk.flows.llm_flows.base_llm_flow").setLevel(logging.ERROR)
logging.getLogger("websockets.client").setLevel(logging.ERROR)
logging.getLogger("websockets.protocol").setLevel(logging.ERROR)
logging.getLogger("websockets.server").setLevel(logging.ERROR)

logger = logging.getLogger(__name__)

# Application configuration
APP_NAME = "interview_orchestrator"
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://localhost:5432/interview_db")

# Store active sessions for post-interview sync
active_sessions = {}


async def _start_agent_session(user_id: str, interview_id: str, is_audio: bool = False):
    """Start an agent session with InMemoryRunner (fast, zero latency)."""

    # Create a Runner per session - InMemory for real-time performance
    runner = InMemoryRunner(app_name=APP_NAME, agent=root_agent)

    # Create a Session with interview_id in state
    session = await runner.session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
        state={"interview_id": interview_id},  # Store interview context
    )

    # Store session and runner for later DB sync
    session_key = f"{user_id}:{interview_id}"
    active_sessions[session_key] = {
        "session": session,
        "runner": runner,
        "user_id": user_id,
        "interview_id": interview_id,
    }

    # Create a LiveRequestQueue for this session
    live_request_queue = LiveRequestQueue()

    # Setup RunConfig
    # NOTE: session_resumption with transparent=True is NOT supported in current Gemini API
    # IMPORTANT: When using test_multiagent, agents already have speech_config in Gemini() wrapper
    # so we should NOT set it again in RunConfig to avoid conflicts

    # Minimal RunConfig - speech_config is in agent models
    run_config = RunConfig(
        streaming_mode="bidi",
        response_modalities=["AUDIO"],
        output_audio_transcription={},
        input_audio_transcription={},
    )

    # Start agent session
    live_events = runner.run_live(
        session=session,
        live_request_queue=live_request_queue,
        run_config=run_config,
    )

    return live_events, live_request_queue, session_key


def should_sync_event(event) -> bool:
    """Filter to only sync text transcriptions (skip audio chunks).

    Transcriptions can be in TWO places:
    1. event.input_transcription (user speech transcribed by Gemini)
    2. event.output_transcription (agent speech transcribed by Gemini)
    3. content.parts[].text (model text responses)
    """
    # Check for user input transcription (Gemini Live API transcribes user audio)
    if hasattr(event, 'input_transcription') and event.input_transcription:
        if hasattr(event.input_transcription, 'text') and event.input_transcription.text:
            if event.input_transcription.text.strip():
                return True

    # Check for agent output transcription (Gemini transcribes its own audio output)
    if hasattr(event, 'output_transcription') and event.output_transcription:
        if hasattr(event.output_transcription, 'text') and event.output_transcription.text:
            if event.output_transcription.text.strip():
                return True

    # Check for text in content.parts (model text responses)
    if hasattr(event, 'content') and event.content and hasattr(event.content, 'parts'):
        for part in event.content.parts:
            if hasattr(part, 'text') and part.text:
                if part.text.strip():
                    return True

            # Future: Could also keep function calls for context
            # if hasattr(part, 'function_call') or hasattr(part, 'function_response'):
            #     return True

    return False


def enrich_event_content_with_transcriptions(event):
    """Add transcription text to event.content so it persists to database.

    ADK's append_event() only stores the 'content' field to the database.
    The input_transcription and output_transcription fields are NOT persisted.

    This function copies transcription data into content.parts[] or custom_metadata
    so the text survives the database write.

    Returns a NEW event object with enriched content (does not mutate original).
    """
    # Import needed for creating new Content/Part objects
    import copy

    from google.genai.types import Content, Part

    # Create a shallow copy to avoid mutating the original event
    enriched_event = copy.copy(event)

    # Check if event has transcriptions that need to be preserved
    has_input_trans = (hasattr(event, 'input_transcription') and
                      event.input_transcription and
                      hasattr(event.input_transcription, 'text') and
                      event.input_transcription.text)

    has_output_trans = (hasattr(event, 'output_transcription') and
                       event.output_transcription and
                       hasattr(event.output_transcription, 'text') and
                       event.output_transcription.text)

    # If no transcriptions to preserve, return original event
    if not (has_input_trans or has_output_trans):
        return enriched_event

    # Build new content that includes transcription text
    if has_input_trans:
        # User speech transcription
        text = event.input_transcription.text
        enriched_event.content = Content(
            role="user",
            parts=[Part.from_text(text=text)]
        )
    elif has_output_trans:
        # Agent speech transcription
        text = event.output_transcription.text
        enriched_event.content = Content(
            role="model",
            parts=[Part.from_text(text=text)]
        )

    return enriched_event


async def sync_session_to_database(user_id: str, interview_id: str) -> dict:
    """Sync InMemory session to Neon DB for persistence.

    Called when interview ends. Transfers all session data from memory to database.

    IMPORTANT: Only syncs FINAL text transcriptions (not audio chunks or partial updates).
    This reduces sync time from ~50 minutes to under 2 minutes.

    Args:
        user_id: User identifier
        interview_id: Interview identifier

    Returns:
        dict with sync status and statistics
    """
    session_key = f"{user_id}:{interview_id}"

    # Check if session exists
    if session_key not in active_sessions:
        logger.warning(f"Session {session_key} not found in active sessions")
        return {
            "success": False,
            "error": "Session not found",
            "session_key": session_key,
        }

    try:
        # Get InMemory session data
        session_data = active_sessions[session_key]
        in_memory_session = session_data["session"]

        logger.info(f"Syncing session {session_key} to database...")
        logger.info(f"  Total events in memory: {len(in_memory_session.events)}")

        # Filter events to text transcriptions only
        filtered_events = []
        for event in in_memory_session.events:
            if should_sync_event(event):
                filtered_events.append(event)

        logger.info(f"  Filtered to {len(filtered_events)} text transcription events")

        # Create DatabaseSessionService
        # Note: ADK tables (adk_sessions, adk_events) will be created in public schema
        # because Neon pooler doesn't support search_path in connection options
        db_service = DatabaseSessionService(db_url=DATABASE_URL)

        # Create new session in database with same data
        db_session = await db_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            state=in_memory_session.state,  # Transfer state (includes interview_id)
        )

        logger.info(f"Created DB session: {db_session.id}")

        # Sync filtered events to database in batches
        total_events = len(filtered_events)
        synced_events = 0
        failed_events = 0
        batch_size = 50  # Sync 50 events in parallel per batch

        logger.info(f"Starting batch sync of {total_events} events (batch_size={batch_size})...")

        for i in range(0, total_events, batch_size):
            batch = filtered_events[i : i + batch_size]

            # Enrich events with transcription data before syncing
            # (ADK's append_event only persists content field)
            enriched_batch = [
                enrich_event_content_with_transcriptions(event) for event in batch
            ]

            # Sync batch in parallel using asyncio.gather
            tasks = [
                db_service.append_event(session=db_session, event=event)
                for event in enriched_batch
            ]

            try:
                # Execute all tasks in this batch concurrently
                results = await asyncio.gather(*tasks, return_exceptions=True)

                # Count successes and failures
                for idx, result in enumerate(results):
                    if isinstance(result, Exception):
                        failed_events += 1
                        logger.error(f"Failed to sync event {i+idx+1}/{total_events}: {result}")
                    else:
                        synced_events += 1

            except Exception as batch_error:
                logger.error(f"Batch sync failed: {batch_error}")
                failed_events += len(batch)

        # Final summary
        logger.info(
            f"Sync complete: {synced_events} succeeded, "
            f"{failed_events} failed, {total_events} total"
        )

        # Cleanup - remove from active sessions
        del active_sessions[session_key]

        return {
            "success": True,
            "session_key": session_key,
            "db_session_id": db_session.id,
            "events_synced": synced_events,
            "events_failed": failed_events,
            "total_events": total_events,
            "state": in_memory_session.state,
        }

    except Exception as e:
        logger.error(f"Failed to sync session {session_key}: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e),
            "session_key": session_key,
        }


async def _agent_to_client_messaging(websocket: WebSocket, live_events):
    """Stream agent responses to the WebSocket client.

    Uses structured message format matching the working ADK sample.
    Each message contains all event data in a single structured object.
    """
    try:
        async for event in live_events:
            # Create structured message matching working ADK sample format
            message_to_send = {
                "author": event.author or "agent",
                "is_partial": event.partial or False,
                "turn_complete": event.turn_complete or False,
                "interrupted": event.interrupted or False,
                "parts": [],
                "input_transcription": None,
                "output_transcription": None,
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
                await websocket.send_text(json_message)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"Error in agent_to_client_messaging: {e}", exc_info=True)


async def _client_to_agent_messaging(websocket: WebSocket, live_request_queue: LiveRequestQueue):
    """Relay client messages to the ADK agent."""
    try:
        while True:
            message_json = await websocket.receive_text()
            message = json.loads(message_json)
            mime_type = message["mime_type"]
            data = message["data"]

            if mime_type == "text/plain":
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
        pass
    except Exception as e:
        logger.error(f"Error in client_to_agent_messaging: {e}", exc_info=True)


# FastAPI application
app = FastAPI(title="Interview Orchestrator")

# Static files
STATIC_DIR = Path("static")
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def root():
    """Serve index.html if it exists."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "Interview Orchestrator is running. Connect via WebSocket at /ws/{user_id}"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "agent": root_agent.name}


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(
    websocket: WebSocket, user_id: str, interview_id: str, is_audio: str = "false"
):
    """WebSocket endpoint for bidirectional communication with the agent.

    Args:
        user_id: Unique client identifier (UUID string)
        interview_id: Interview ID to associate with this session (required)
        is_audio: "true" for audio mode, "false" for text mode
    """
    logger.info(f"WebSocket connection starting for user={user_id}, interview={interview_id}")

    await websocket.accept()

    live_events, live_request_queue, session_key = await _start_agent_session(
        user_id, interview_id, is_audio == "true"
    )
    logger.info(f"Agent session started: {session_key}")

    # Run bidirectional messaging concurrently
    agent_to_client_task = asyncio.create_task(_agent_to_client_messaging(websocket, live_events))
    client_to_agent_task = asyncio.create_task(
        _client_to_agent_messaging(websocket, live_request_queue)
    )

    try:
        tasks = [agent_to_client_task, client_to_agent_task]

        # Wait for first task to complete (disconnect, error, or natural completion)
        # Using FIRST_COMPLETED instead of FIRST_EXCEPTION to avoid deadlock
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

        # Cancel any pending tasks to prevent deadlock
        if pending:
            for task in pending:
                task.cancel()

            # Wait for cancellation to complete (with timeout for safety)
            try:
                await asyncio.wait_for(
                    asyncio.gather(*pending, return_exceptions=True),
                    timeout=5.0
                )
            except asyncio.TimeoutError:
                logger.warning(f"Timeout waiting for task cancellation: {session_key}")
            except Exception as cancel_error:
                logger.error(f"Error during task cancellation: {cancel_error}")

        # Check for exceptions in completed tasks
        for task in done:
            try:
                exception = task.exception()
                if exception is not None:
                    logger.error(f"Task error for {session_key}: {exception}")
            except asyncio.CancelledError:
                pass

    except Exception as e:
        logger.error(f"Exception in websocket endpoint for {session_key}: {e}", exc_info=True)
    finally:
        # Close queue to signal live_events to stop
        try:
            live_request_queue.close()
        except Exception as close_error:
            logger.error(f"Error closing queue for {session_key}: {close_error}")

        # Sync session to database when connection closes
        logger.info(f"Starting session sync for {session_key}")
        try:
            sync_result = await sync_session_to_database(user_id, interview_id)

            if sync_result["success"]:
                synced = sync_result['events_synced']
                failed = sync_result.get('events_failed', 0)
                total = sync_result['total_events']

                if failed > 0:
                    logger.warning(
                        f"Session synced with errors: "
                        f"{synced} succeeded, {failed} failed, {total} total"
                    )
                else:
                    logger.info(f"Session synced successfully: {synced}/{total} events")
            else:
                logger.error(
                    f"Session sync failed: {sync_result.get('error', 'Unknown error')}"
                )
        except Exception as sync_error:
            logger.error(
                f"Critical error during sync for {session_key}: {sync_error}", exc_info=True
            )


def start_server(host: str = "0.0.0.0", port: int = 8080, reload: bool = False) -> None:
    """Start the FastAPI server.

    Args:
        host: Host to bind to
        port: Port to run on
        reload: Enable auto-reload for development
    """
    logger.info(f"Starting Interview Orchestrator on {host}:{port}")
    uvicorn.run(app, host=host, port=port, reload=reload)
