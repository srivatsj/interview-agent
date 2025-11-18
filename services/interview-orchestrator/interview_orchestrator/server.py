"""WebSocket Server for Interview Orchestrator.

FastAPI server enabling real-time bidirectional communication with ADK agent.
Uses BIDI streaming for user interruption support.

This module now delegates to the websocket package for all functionality.
"""

import logging
import warnings

from dotenv import load_dotenv

from .websocket import app, start_server

# Load environment variables
load_dotenv()

# Configure logging - suppress verbose logs
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# Suppress noisy loggers completely (set to ERROR to only show critical issues)
logging.getLogger("google_adk.google.adk.flows.llm_flows.audio_cache_manager").setLevel(
    logging.ERROR
)
logging.getLogger("google_adk.google.adk.models.gemini_llm_connection").setLevel(logging.ERROR)
logging.getLogger("google_adk.google.adk.models.google_llm").setLevel(logging.ERROR)
logging.getLogger("google_adk.google.adk.flows.llm_flows.base_llm_flow").setLevel(logging.ERROR)
logging.getLogger("websockets.client").setLevel(logging.ERROR)
logging.getLogger("websockets.protocol").setLevel(logging.ERROR)
logging.getLogger("websockets.server").setLevel(logging.ERROR)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)  # Suppress access logs

# Suppress pydantic serializer warnings
warnings.filterwarnings("ignore", message=".*UserWarning.*EXPERIMENTAL.*")
warnings.filterwarnings("ignore", message=".*Pydantic serializer warnings.*")

# Export app and start_server for backward compatibility
__all__ = ["app", "start_server"]
