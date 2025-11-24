"""Shared constants for the interview orchestrator."""

import os

from google.adk.models.google_llm import Gemini
from google.genai import types


def get_gemini_model() -> Gemini:
    """Get configured Gemini model.

    Production (ENV=prod): Uses native-audio model with speech_config for audio mode.
    Dev/Test (ENV=dev/test): Uses standard Live API model for TEXT modality.

    Returns:
        Gemini model with appropriate configuration.
    """
    env = os.getenv("ENV", "dev").lower()

    if env == "prod":
        # Production: native-audio model with speech configuration
        model_name = os.getenv("AGENT_MODEL", "gemini-2.5-flash-native-audio-preview-09-2025")
        return Gemini(
            model=model_name,
            speech_config=types.SpeechConfig(
                language_code=os.getenv("AGENT_LANGUAGE", "en-US"),
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=os.getenv("AGENT_VOICE", "Kore")
                    )
                ),
            ),
        )
    else:
        # Dev/Test: standard Live API model (supports TEXT modality)
        # Use a model that doesn't trigger automatic audio transcription
        return Gemini(model="gemini-2.0-flash-live-001")
