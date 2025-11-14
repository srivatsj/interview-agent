"""Shared constants for the interview orchestrator."""

import os

from google.adk.models.google_llm import Gemini
from google.genai import types


def get_gemini_model() -> Gemini:
    """Get configured Gemini model with speech settings.

    Returns:
        Gemini model with speech configuration from environment.
    """
    return Gemini(
        model=os.getenv("AGENT_MODEL", "gemini-2.5-flash-native-audio-preview-09-2025"),
        speech_config=types.SpeechConfig(
            language_code=os.getenv("AGENT_LANGUAGE", "en-US"),
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=os.getenv("AGENT_VOICE", "Kore")
                )
            ),
        ),
    )
