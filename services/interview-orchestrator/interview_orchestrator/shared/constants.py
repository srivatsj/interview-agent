"""
Constants used across the interview agent system.
"""

from google.adk.models.google_llm import Gemini
from google.genai import types

# Model configuration for Live API with bidirectional audio/video streaming
# Using native audio preview model for real-time audio input/output
MODEL_NAME = "gemini-2.5-flash-native-audio-preview-09-2025"

# Model with audio output configuration for Live API
# speech_config enables audio responses over WebSocket
# Available voices: Puck, Charon, Kore, Fenrir, Aoede
MODEL_WITH_AUDIO = Gemini(
    model=MODEL_NAME,
    speech_config=types.SpeechConfig(
        voice_config=types.VoiceConfig(
            prebuilt_voice_config=types.PrebuiltVoiceConfig(
                voice_name="Puck",  # Professional, clear voice
            )
        )
    ),
)
