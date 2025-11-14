"""WebSocket Server for Interview Orchestrator.

FastAPI server enabling real-time bidirectional communication with ADK agent.
Uses BIDI streaming for user interruption support.
"""

import asyncio
import base64
import json
import logging
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


async def _start_agent_session(user_id: str, is_audio: bool = False):
    """Start an agent session."""

    # Create a Runner per session
    runner = InMemoryRunner(app_name=APP_NAME, agent=root_agent)

    # Create a Session
    session = await runner.session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
    )

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

    return live_events, live_request_queue


async def _agent_to_client_messaging(websocket: WebSocket, live_events):
    """Stream agent responses to the WebSocket client.

    Uses structured message format matching the working ADK sample.
    Each message contains all event data in a single structured object.
    """
    logger.info("Agent-to-client messaging started")
    event_count = 0
    try:
        async for event in live_events:
            event_count += 1
            logger.debug(f"Event #{event_count} received from {event.author}")
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
                    logger.info(
                        f"Turn event from {event.author}: "
                        f"complete={message_to_send['turn_complete']}, "
                        f"interrupted={message_to_send['interrupted']}"
                    )
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
                    if not event.partial:
                        logger.info(f"User: {transcription_text}")

            # Handle agent/model responses (role can be "model", "agent", or None)
            elif not (hasattr(event.content, "role") and event.content.role == "user"):
                # Add output transcription if available
                if transcription_text:
                    message_to_send["output_transcription"] = {
                        "text": transcription_text,
                        "is_final": not event.partial,
                    }
                    message_to_send["parts"].append({"type": "text", "data": transcription_text})
                    if not event.partial:
                        logger.info(f"{event.author}: {transcription_text}")

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
                        logger.info(f"{event.author} -> {part.function_call.name}()")

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
        logger.info("Client disconnected from agent_to_client_messaging")
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
                logger.debug(f"Text message from client: {data}")
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
                logger.debug(f"Image from client: {len(decoded_data)} bytes")
            else:
                raise ValueError(f"Mime type not supported: {mime_type}")

    except WebSocketDisconnect:
        logger.info("Client disconnected from client_to_agent_messaging")
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
async def websocket_endpoint(websocket: WebSocket, user_id: str, is_audio: str = "false"):
    """WebSocket endpoint for bidirectional communication with the agent.

    Args:
        user_id: Unique client identifier (UUID string)
        is_audio: "true" for audio mode, "false" for text mode
    """
    await websocket.accept()
    logger.info(f"Client {user_id} connected (audio={is_audio})")

    live_events, live_request_queue = await _start_agent_session(user_id, is_audio == "true")
    logger.info(f"Agent session started for user {user_id}")

    # Run bidirectional messaging concurrently
    agent_to_client_task = asyncio.create_task(_agent_to_client_messaging(websocket, live_events))
    client_to_agent_task = asyncio.create_task(
        _client_to_agent_messaging(websocket, live_request_queue)
    )

    try:
        tasks = [agent_to_client_task, client_to_agent_task]
        done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_EXCEPTION)

        for task in done:
            if task.exception() is not None:
                logger.error(f"Task error for client #{user_id}: {task.exception()}")
    finally:
        live_request_queue.close()
        logger.info(f"Client #{user_id} disconnected")


def start_server(host: str = "0.0.0.0", port: int = 8080, reload: bool = False) -> None:
    """Start the FastAPI server.

    Args:
        host: Host to bind to
        port: Port to run on
        reload: Enable auto-reload for development
    """
    logger.info(f"Starting Interview Orchestrator on {host}:{port}")
    uvicorn.run(app, host=host, port=port, reload=reload)
