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
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.genai import types
from google.genai.types import Blob, Content, Part

from .root_agent import root_agent

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Application configuration
APP_NAME = "interview_orchestrator"

# Initialize session service
session_service = InMemorySessionService()

# Create Runner instance
runner = Runner(
    app_name=APP_NAME,
    agent=root_agent,
    session_service=session_service,
)


async def _start_agent_session(user_id: str, is_audio: bool = False):
    """Start an agent session with bidirectional streaming.

    Args:
        user_id: Unique client identifier
        is_audio: True for audio responses, False for text

    Returns:
        Tuple of (live_events, live_request_queue)
    """
    session_id = f"{APP_NAME}_{user_id}"
    session = await runner.session_service.get_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session_id,
    )
    if not session:
        session = await runner.session_service.create_session(
            app_name=APP_NAME,
            user_id=user_id,
            session_id=session_id,
        )

    # Configure response format
    model_name = root_agent.model if isinstance(root_agent.model, str) else root_agent.model.model
    is_native_audio = "native-audio" in model_name.lower()
    modality = "AUDIO" if (is_audio or is_native_audio) else "TEXT"

    run_config = RunConfig(
        streaming_mode=StreamingMode.BIDI,
        response_modalities=[modality],
        session_resumption=types.SessionResumptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig()
        if (is_audio or is_native_audio)
        else None,
    )

    live_request_queue = LiveRequestQueue()

    live_events = runner.run_live(
        user_id=user_id,
        session_id=session.id,
        live_request_queue=live_request_queue,
        run_config=run_config,
    )

    return live_events, live_request_queue


async def _agent_to_client_messaging(websocket: WebSocket, live_events):
    """Stream agent responses to the WebSocket client."""
    try:
        async for event in live_events:
            # Handle output audio transcription
            if event.output_transcription and event.output_transcription.text:
                transcript_text = event.output_transcription.text
                message = {
                    "mime_type": "text/plain",
                    "data": transcript_text,
                    "is_transcript": True,
                }
                await websocket.send_text(json.dumps(message))
                logger.debug(f"[AGENT TO CLIENT]: audio transcript: {transcript_text}")

            # Read the Content and its first Part
            part: Part = event.content and event.content.parts and event.content.parts[0]
            if part:
                # Handle audio data
                is_audio = part.inline_data and part.inline_data.mime_type.startswith("audio/pcm")
                if is_audio:
                    audio_data = part.inline_data and part.inline_data.data
                    if audio_data:
                        message = {
                            "mime_type": "audio/pcm",
                            "data": base64.b64encode(audio_data).decode("ascii"),
                        }
                        await websocket.send_text(json.dumps(message))
                        logger.debug(f"[AGENT TO CLIENT]: audio/pcm: {len(audio_data)} bytes")

                # Handle text data (partial streaming)
                if part.text and event.partial:
                    message = {"mime_type": "text/plain", "data": part.text}
                    await websocket.send_text(json.dumps(message))
                    logger.debug(f"[AGENT TO CLIENT]: text/plain: {part.text}")

            # Handle turn completion and interruption
            if event.turn_complete or event.interrupted:
                message = {
                    "turn_complete": event.turn_complete,
                    "interrupted": event.interrupted,
                }
                await websocket.send_text(json.dumps(message))
                logger.debug(f"[AGENT TO CLIENT]: {message}")

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
                logger.debug(f"[CLIENT TO AGENT]: {data}")
            elif mime_type == "audio/pcm":
                decoded_data = base64.b64decode(data)
                live_request_queue.send_realtime(Blob(data=decoded_data, mime_type=mime_type))
                logger.debug(f"[CLIENT TO AGENT]: audio/pcm: {len(decoded_data)} bytes")
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
async def websocket_endpoint(websocket: WebSocket, user_id: int, is_audio: str = "false"):
    """WebSocket endpoint for bidirectional communication with the agent.

    Args:
        user_id: Unique client identifier
        is_audio: "true" for audio mode, "false" for text mode
    """
    await websocket.accept()
    logger.info(f"Client #{user_id} connected, audio mode: {is_audio}")

    user_id_str = str(user_id)
    live_events, live_request_queue = await _start_agent_session(user_id_str, is_audio == "true")

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
