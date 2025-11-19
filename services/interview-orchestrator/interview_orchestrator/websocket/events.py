"""Event filtering and enrichment for session synchronization."""

import copy

from google.genai.types import Content, Part


def should_sync_event(event) -> bool:
    """Filter to only sync text transcriptions (skip audio chunks).

    Transcriptions can be in TWO places:
    1. event.input_transcription (user speech transcribed by Gemini)
    2. event.output_transcription (agent speech transcribed by Gemini)
    3. content.parts[].text (model text responses)
    """
    # Check for user input transcription (Gemini Live API transcribes user audio)
    if hasattr(event, "input_transcription") and event.input_transcription:
        if hasattr(event.input_transcription, "text") and event.input_transcription.text:
            if event.input_transcription.text.strip():
                return True

    # Check for agent output transcription (Gemini transcribes its own audio output)
    if hasattr(event, "output_transcription") and event.output_transcription:
        if hasattr(event.output_transcription, "text") and event.output_transcription.text:
            if event.output_transcription.text.strip():
                return True

    # Check for text in content.parts (model text responses)
    if hasattr(event, "content") and event.content and hasattr(event.content, "parts"):
        for part in event.content.parts:
            if hasattr(part, "text") and part.text:
                if part.text.strip():
                    return True

            # Future: Could also keep function calls for context
            # if hasattr(part, 'function_call') or hasattr(part, 'function_response'):
            #     return True

    return False


def enrich_event_content_with_transcriptions(event):
    """Add transcription text to event.content so it persists to database.

    ADK's append_event() only stores the 'content' field to the database.
    The input_transcription and output_transcription fields are NOT persisted.

    This function copies transcription data into content.parts[] or custom_metadata
    so the text survives the database write.

    Returns a NEW event object with enriched content (does not mutate original).
    """
    # Create a shallow copy to avoid mutating the original event
    enriched_event = copy.copy(event)

    # Check if event has transcriptions that need to be preserved
    has_input_trans = (
        hasattr(event, "input_transcription")
        and event.input_transcription
        and hasattr(event.input_transcription, "text")
        and event.input_transcription.text
    )

    has_output_trans = (
        hasattr(event, "output_transcription")
        and event.output_transcription
        and hasattr(event.output_transcription, "text")
        and event.output_transcription.text
    )

    # If no transcriptions to preserve, return original event
    if not (has_input_trans or has_output_trans):
        return enriched_event

    # Build new content that includes transcription text
    if has_input_trans:
        # User speech transcription
        text = event.input_transcription.text
        enriched_event.content = Content(role="user", parts=[Part.from_text(text=text)])
    elif has_output_trans:
        # Agent speech transcription
        text = event.output_transcription.text
        enriched_event.content = Content(role="model", parts=[Part.from_text(text=text)])

    return enriched_event
