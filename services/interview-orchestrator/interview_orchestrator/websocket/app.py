"""FastAPI application for Interview Orchestrator WebSocket server."""

import asyncio
import logging
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI, WebSocket
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from google.adk.sessions import DatabaseSessionService

from ..root_agent import root_agent
from ..shared.session_store import active_sessions
from .agent_to_client import agent_to_client_messaging
from .client_to_agent import client_to_agent_messaging
from .session import start_agent_session, sync_session_to_database

logger = logging.getLogger(__name__)

# FastAPI application
app = FastAPI(title="Interview Orchestrator")


@app.on_event("startup")
async def initialize_database():
    """Initialize ADK database tables on startup."""
    database_url = os.getenv("DATABASE_URL", "postgresql://localhost:5432/interview_db")
    logger.info(f"Initializing ADK database tables at {database_url}")

    try:
        # Create DatabaseSessionService to trigger table creation
        db_service = DatabaseSessionService(db_url=database_url)

        # Create a dummy session to ensure tables are created
        # This will create adk_sessions and adk_events tables
        dummy_session = await db_service.create_session(
            app_name="interview_orchestrator",
            user_id="init",
            state={"initialized": True}
        )

        # Delete the dummy session (requires app_name, user_id, and session_id)
        await db_service.delete_session(
            app_name="interview_orchestrator",
            user_id="init",
            session_id=dummy_session.id
        )

        logger.info("✅ ADK database tables initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize ADK database tables: {e}")
        # Don't raise - allow app to start even if DB init fails
        # Tables will be created on first session sync instead

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
    await websocket.accept()

    live_events, live_request_queue, session_key = await start_agent_session(
        user_id, interview_id, is_audio == "true"
    )

    # Store websocket reference for tools to send direct notifications
    active_sessions[session_key]["websocket"] = websocket

    logger.info(f"🔗 WebSocket connected: {session_key}")

    # Run bidirectional messaging concurrently
    agent_to_client_task = asyncio.create_task(
        agent_to_client_messaging(websocket, live_events, session_key, active_sessions)
    )
    client_to_agent_task = asyncio.create_task(
        client_to_agent_messaging(websocket, live_request_queue, session_key, active_sessions)
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
                    asyncio.gather(*pending, return_exceptions=True), timeout=5.0
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
                synced = sync_result["events_synced"]
                failed = sync_result.get("events_failed", 0)
                total = sync_result["total_events"]

                if failed > 0:
                    logger.warning(
                        f"Session synced with errors: "
                        f"{synced} succeeded, {failed} failed, {total} total"
                    )
                else:
                    logger.info(f"Session synced successfully: {synced}/{total} events")
            else:
                logger.error(f"Session sync failed: {sync_result.get('error', 'Unknown error')}")
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
