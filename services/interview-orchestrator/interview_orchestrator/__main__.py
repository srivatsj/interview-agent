"""
Interview Orchestrator - WebSocket Server Entry Point

Starts a FastAPI server with WebSocket support for real-time interview sessions.
Uses ADK's built-in server infrastructure with LiveRequestQueue for bidirectional streaming.

Usage:
    python -m interview_orchestrator [OPTIONS]

The server exposes a WebSocket endpoint at /run_live that accepts:
- Audio chunks (realtime mode via blob)
- Screenshots (realtime mode via blob)
- Text messages (turn-by-turn mode via content)

Example WebSocket URL:
    ws://localhost:8080/run_live?app_name=interview_router&user_id=<user_id>&session_id=<session_id>
"""

import click
from dotenv import load_dotenv

from .server import start_server

# Load environment variables
load_dotenv()


@click.command()
@click.option("--host", default="127.0.0.1", help="Host to bind the server to")
@click.option("--port", default=8080, help="Port to run the server on")
@click.option("--reload/--no-reload", default=False, help="Enable auto-reload for development")
def main(host: str, port: int, reload: bool):
    """Start the Interview Orchestrator WebSocket server."""
    click.echo(f"Starting Interview Orchestrator server on {host}:{port}")
    click.echo(f"WebSocket endpoint: ws://{host}:{port}/run_live")
    start_server(host=host, port=port, reload=reload)


if __name__ == "__main__":
    main()
