"""
WebSocket Server for Interview Orchestrator

Leverages ADK's built-in FastAPI server with WebSocket support.
Uses LiveRequestQueue for bidirectional streaming of audio, screenshots, and text.
"""

import logging

from google.adk.apps import App

from .root_agent import RootCustomAgent

logger = logging.getLogger(__name__)


def create_app() -> App:
    """Create an ADK App with the root interview orchestrator agent.

    Returns:
        App: ADK application ready to be served
    """
    root_agent = RootCustomAgent()

    app = App(
        name="interview_orchestrator",
        root_agent=root_agent,
    )

    logger.info("Interview Orchestrator app created successfully")
    return app


def start_server(host: str = "127.0.0.1", port: int = 8080, reload: bool = False) -> None:
    """Start the FastAPI server with WebSocket support.

    Uses ADK's built-in API server which provides:
    - WebSocket endpoint at /run_live
    - Session management
    - LiveRequestQueue for bidirectional streaming

    Args:
        host: Host to bind the server to
        port: Port to run the server on
        reload: Enable auto-reload for development

    WebSocket Message Format (from frontend):
        {
            "blob": {
                "mime_type": "audio/webm" | "image/png",
                "data": "<base64_encoded_data>"
            }
        }
        OR
        {
            "content": {
                "parts": [{"text": "user message"}]
            }
        }

    WebSocket Message Format (to frontend):
        ADK Event objects serialized to JSON
    """
    # ADK CLI command equivalent: adk api_server --host <host> --port <port>
    # We use the programmatic API here for more control

    # Import inside function to avoid import errors at module level (ruff: PLC0415 disabled)
    import uvicorn
    from google.adk.cli.adk_web_server import AdkWebServer
    from google.adk.cli.utils.base_agent_loader import StaticAgentLoader
    from google.adk.sessions.in_memory_session_service import InMemorySessionService

    # Create services
    session_service = InMemorySessionService()

    # Create static agent loader with our app
    app = create_app()
    agent_loader = StaticAgentLoader(agents_or_apps={"interview_orchestrator": app})

    # Create ADK web server
    adk_server = AdkWebServer(
        agent_loader=agent_loader,
        session_service=session_service,
        memory_service=None,  # Not needed for basic interviews
        artifact_service=None,  # Not needed for basic interviews
        credential_service=None,  # Not needed for basic interviews
        eval_sets_manager=None,  # Not needed
        eval_set_results_manager=None,  # Not needed
        agents_dir="",  # Not used with StaticAgentLoader
    )

    # Create FastAPI app with WebSocket endpoint
    fastapi_app = adk_server.create_app(web_assets_dir=None)

    logger.info(f"Starting server on {host}:{port}")
    logger.info(f"WebSocket endpoint: ws://{host}:{port}/run_live")
    logger.info("Query params: app_name=interview_orchestrator&user_id=<id>&session_id=<id>")

    # Start server
    uvicorn.run(
        fastapi_app,
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )
