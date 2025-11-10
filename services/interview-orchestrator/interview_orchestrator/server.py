"""
WebSocket Server for Interview Orchestrator

Leverages ADK's built-in FastAPI server with WebSocket support.
Uses LiveRequestQueue for bidirectional streaming of audio, screenshots, and text.

Implements bidirectional streaming (BIDI mode) for proper user interruption handling.
"""

import logging

from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.apps import App

from .root_agent import root_agent

logger = logging.getLogger(__name__)


def create_run_config() -> RunConfig:
    """Create RunConfig with bidirectional streaming for user interruptions.

    Returns:
        RunConfig: Configuration enabling BIDI streaming mode
    """
    return RunConfig(
        streaming_mode=StreamingMode.BIDI,  # Enable bidirectional streaming
    )


def create_app() -> App:
    """Create an ADK App with the root interview orchestrator agent.

    Returns:
        App: ADK application ready to be served
    """
    app = App(
        name="interview_orchestrator",
        root_agent=root_agent,
    )

    logger.info("Interview Orchestrator app created successfully")
    return app


def start_server(host: str = "127.0.0.1", port: int = 8080, reload: bool = False) -> None:
    """Start the FastAPI server with WebSocket support.

    Uses ADK's built-in API server with custom WebSocket endpoint supporting:
    - Bidirectional streaming (BIDI mode) for user interruptions
    - LiveRequestQueue for real-time audio/video/text streaming
    - Session management with persistent state

    Args:
        host: Host to bind the server to
        port: Port to run the server on
        reload: Enable auto-reload for development

    WebSocket Endpoint:
        ws://<host>:<port>/run_live?app_name=interview_orchestrator&user_id=<id>&session_id=<id>

    WebSocket Message Format (from frontend):
        Audio chunk: {"blob": {"mime_type": "audio/webm", "data": "<base64>"}}
        Screenshot: {"blob": {"mime_type": "image/png", "data": "<base64>"}}
        Text: {"content": {"parts": [{"text": "user message"}]}}

    WebSocket Message Format (to frontend):
        ADK Event objects serialized to JSON (agent_content, tool_call, etc.)

    Bidirectional Streaming (BIDI):
        - User can interrupt AI mid-speech
        - AI stops speaking when interrupted
        - AI processes user's interruption immediately
        - Seamless turn-taking in voice conversations
    """
    # Import inside function to avoid import errors at module level (ruff: PLC0415 disabled)
    import uvicorn
    from fastapi import FastAPI, Query, WebSocket
    from google.adk.runners import InMemoryRunner
    from google.adk.sessions.in_memory_session_service import InMemorySessionService
    from google.adk.streaming.live_request_queue import LiveRequestQueue

    # Create services
    session_service = InMemorySessionService()
    runner = InMemoryRunner(session_service=session_service)

    # Create FastAPI app
    app_instance = FastAPI(title="Interview Orchestrator")

    # Create ADK app
    adk_app = create_app()

    # Create RunConfig with BIDI streaming
    run_config = create_run_config()

    @app_instance.websocket("/run_live")
    async def websocket_endpoint(
        websocket: WebSocket,
        app_name: str = Query(...),
        user_id: str = Query(...),
        session_id: str = Query(...),
    ):
        """Custom WebSocket endpoint with bidirectional streaming support."""
        await websocket.accept()
        logger.info(f"WebSocket connected: app={app_name}, user={user_id}, session={session_id}")

        # Create LiveRequestQueue for bidirectional streaming
        live_queue = LiveRequestQueue(websocket)

        try:
            # Run agent with BIDI streaming enabled
            async for event in runner.run_live(
                app=adk_app,
                app_name=app_name,
                user_id=user_id,
                session_id=session_id,
                live_request_queue=live_queue,
                run_config=run_config,  # ✅ Enable BIDI streaming for interruptions
            ):
                # Events are automatically sent to frontend via LiveRequestQueue
                logger.debug(f"Event: {event.type if hasattr(event, 'type') else event}")

        except Exception as e:
            logger.error(f"WebSocket error: {e}", exc_info=True)
            await websocket.close(code=1011, reason=str(e))
        finally:
            logger.info(f"WebSocket closed: user={user_id}, session={session_id}")

    logger.info(f"Starting server on {host}:{port}")
    logger.info(f"WebSocket endpoint: ws://{host}:{port}/run_live")
    logger.info("Query params: app_name=interview_orchestrator&user_id=<id>&session_id=<id>")
    logger.info("✅ Bidirectional streaming (BIDI) enabled for user interruptions")

    # Start server
    uvicorn.run(
        app_instance,
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )
