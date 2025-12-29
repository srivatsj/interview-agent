"""WebSocket server for bidirectional audio streaming with Gemini Live API.

This server handles:
1. WebSocket connections from frontend
2. Bidirectional audio streaming
3. Text message fallback
4. Session management
"""

import asyncio
import json
import logging
from typing import Dict, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from google.adk.sessions import InMemorySessionService

from ..agents.simple_interview import root_agent

logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="Orchestrator2 POC - Audio Interview")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Session service
session_service = InMemorySessionService()

# Active WebSocket connections
active_connections: Dict[str, WebSocket] = {}


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "orchestrator2-poc"}


@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    """WebSocket endpoint for bidirectional audio/text communication.

    Args:
        websocket: WebSocket connection
        user_id: Unique user identifier
    """
    await websocket.accept()
    logger.info(f"🔌 WebSocket connected: {user_id}")

    # Store connection
    active_connections[user_id] = websocket

    # Create or get session
    try:
        session = await session_service.create_session(
            app_name="interview_poc",
            user_id=user_id
        )
        logger.info(f"📝 Session created for {user_id}")

        # Send welcome message
        await websocket.send_json({
            "type": "connected",
            "message": "Connected to interview orchestrator",
            "session_id": session.id
        })

        # Handle messages
        while True:
            try:
                # Receive message (text or binary audio)
                raw_message = await websocket.receive()

                if "text" in raw_message:
                    # Text message
                    data = json.loads(raw_message["text"])
                    await handle_text_message(data, session, websocket)

                elif "bytes" in raw_message:
                    # Binary audio data
                    audio_data = raw_message["bytes"]
                    await handle_audio_message(audio_data, session, websocket)

            except WebSocketDisconnect:
                logger.info(f"🔌 WebSocket disconnected: {user_id}")
                break
            except Exception as e:
                logger.error(f"❌ Error handling message: {e}")
                await websocket.send_json({
                    "type": "error",
                    "error": str(e)
                })

    except Exception as e:
        logger.error(f"❌ Session error for {user_id}: {e}")
        await websocket.send_json({
            "type": "error",
            "error": f"Session error: {e}"
        })

    finally:
        # Cleanup
        if user_id in active_connections:
            del active_connections[user_id]
        logger.info(f"🧹 Cleaned up connection for {user_id}")


async def handle_text_message(
    data: Dict[str, Any],
    session: Any,
    websocket: WebSocket
):
    """Handle text message from client.

    Args:
        data: Message data
        session: ADK session
        websocket: WebSocket connection
    """
    message_type = data.get("type")
    content = data.get("content", "")

    logger.info(f"📨 Text message: type={message_type}, content={content[:50]}...")

    if message_type == "message":
        # Send typing indicator
        await websocket.send_json({
            "type": "typing",
            "status": "thinking"
        })

        try:
            # Generate response using ADK agent
            response = await root_agent.generate_content(
                content,
                session=session
            )

            # Send response
            await websocket.send_json({
                "type": "message",
                "content": str(response),
                "phase": session.state.get("phase_complete", "intro"),
                "expert_calls": session.state.get("expert_calls", 0)
            })

            logger.info(f"✅ Response sent: {str(response)[:100]}...")

        except Exception as e:
            logger.error(f"❌ Error generating response: {e}")
            await websocket.send_json({
                "type": "error",
                "error": f"Failed to generate response: {e}"
            })


async def handle_audio_message(
    audio_data: bytes,
    session: Any,
    websocket: WebSocket
):
    """Handle audio data from client (for future Gemini Live integration).

    Args:
        audio_data: Binary audio data
        session: ADK session
        websocket: WebSocket connection
    """
    logger.info(f"🎤 Received audio: {len(audio_data)} bytes")

    # TODO: Integrate with Gemini Live API for audio streaming
    # For now, send acknowledgment
    await websocket.send_json({
        "type": "audio_ack",
        "bytes_received": len(audio_data)
    })


@app.get("/session/{user_id}/state")
async def get_session_state(user_id: str):
    """Get current session state for debugging.

    Args:
        user_id: User identifier

    Returns:
        Session state
    """
    try:
        # Get existing session
        sessions = await session_service.list_sessions(user_id=user_id)
        if not sessions:
            return {"error": "No session found"}

        session = sessions[0]
        return {
            "session_id": session.id,
            "state": dict(session.state),
            "user_id": user_id
        }
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8002,
        log_level="info"
    )
