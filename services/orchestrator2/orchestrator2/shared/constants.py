"""Shared constants for orchestrator2."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


def get_gemini_model() -> str:
    """Get the appropriate Gemini model based on environment.

    For audio/live streaming, we MUST use the -live- model variants.
    For tests, we use standard generateContent API models.

    Returns:
        Model name string (ADK accepts string model names)
    """
    env = os.getenv("ENV", "dev")

    if env == "test":
        # Test: Use standard model for generateContent API (not Live API)
        return "gemini-2.0-flash-exp"
    elif env == "prod":
        # Production: Use gemini-2.0-flash-live for audio support
        return "gemini-2.0-flash-live-001"
    else:
        # Dev: Use -live- version for bidiGenerateContent (audio streaming)
        return "gemini-2.0-flash-live-001"
