"""
LLM Response Recorder/Replayer for Integration Tests

This module provides a "record and replay" system for LLM responses:
- First run with RECORD_MODE=true: Uses real LLM and saves responses
- Subsequent runs: Replays saved responses (no API calls, no cost)
- When code changes: Set RECORD_MODE=true to re-record

Usage:
    export RECORD_MODE=true  # Record mode
    pytest tests/integration/test_interview_flow.py

    # Or in code:
    with LLMRecorder("test_name", record_mode=True) as recorder:
        # Uses real LLM, saves responses
"""

import json
import os
from pathlib import Path
from typing import Optional
from unittest.mock import patch

from google.adk.models.google_llm import Gemini, LlmResponse
from google.genai.types import Content, FunctionCall, Part


class LLMRecorder:
    """Records and replays LLM responses for deterministic testing."""

    def __init__(
        self,
        test_name: str,
        record_mode: Optional[bool] = None,
        recordings_dir: str = "tests/integration/recordings",
    ):
        """
        Initialize the LLM recorder.

        Args:
            test_name: Unique name for this test (used for filename)
            record_mode: If True, record real LLM responses. If False, replay.
                        If None, check RECORD_MODE env var (default: False)
            recordings_dir: Directory to store recordings
        """
        self.test_name = test_name
        self.recordings_dir = Path(recordings_dir)
        self.recordings_file = self.recordings_dir / f"{test_name}.json"

        # Determine mode
        if record_mode is None:
            record_mode = os.environ.get("RECORD_MODE", "false").lower() == "true"
        self.record_mode = record_mode

        self.recorded_responses = []
        self.replay_index = 0
        self._original_method = None
        self._patcher = None

    def __enter__(self):
        """Start recording or replaying."""
        if self.record_mode:
            print(f"🔴 RECORD MODE: Recording LLM responses to {self.recordings_file}")
            self._setup_recording()

            # Save the original method BEFORE patching
            original_method = Gemini.generate_content_async

            # Create a wrapper that captures self correctly
            def record_wrapper(gemini_self, *args, **kwargs):
                return self._record_wrapper(original_method, gemini_self, *args, **kwargs)

            # Patch with the wrapper
            self._patcher = patch(
                "google.adk.models.google_llm.Gemini.generate_content_async", record_wrapper
            )
            self._patcher.__enter__()

        else:
            print(f"▶️  REPLAY MODE: Using recorded responses from {self.recordings_file}")
            self._load_recordings()

            # Patch the Gemini.generate_content_async method
            self._patcher = patch("google.adk.models.google_llm.Gemini.generate_content_async")
            mock_llm = self._patcher.__enter__()
            # In replay mode: return saved responses
            mock_llm.side_effect = self._replay_generator

        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop recording/replaying and save if needed."""
        if self._patcher:
            self._patcher.__exit__(exc_type, exc_val, exc_tb)

        if self.record_mode and not exc_type:
            # Only save if test passed (no exception)
            self._save_recordings()

        return False

    def _setup_recording(self):
        """Prepare for recording mode."""
        self.recordings_dir.mkdir(parents=True, exist_ok=True)
        self.recorded_responses = []

    def _load_recordings(self):
        """Load previously recorded responses."""
        if not self.recordings_file.exists():
            raise FileNotFoundError(
                f"No recordings found at {self.recordings_file}. "
                f"Run with RECORD_MODE=true first to record LLM responses."
            )

        with open(self.recordings_file, "r") as f:
            data = json.load(f)
            self.recorded_responses = data["responses"]
            print(f"✅ Loaded {len(self.recorded_responses)} recorded responses")

    def _save_recordings(self):
        """Save recorded responses to file."""
        data = {
            "test_name": self.test_name,
            "num_responses": len(self.recorded_responses),
            "responses": self.recorded_responses,
        }

        with open(self.recordings_file, "w") as f:
            json.dump(data, f, indent=2)

        print(f"✅ Saved {len(self.recorded_responses)} responses to {self.recordings_file}")

    async def _record_wrapper(self, original_method, gemini_instance, *args, **kwargs):
        """Wrapper that calls real LLM and records responses."""
        # Call the original method with the real Gemini instance
        async for response in original_method(gemini_instance, *args, **kwargs):
            # Serialize and record the response
            serialized = self._serialize_response(response)
            self.recorded_responses.append(serialized)

            # Yield to the test
            yield response

    def _replay_generator(self, *args, **kwargs):
        """Generator that replays recorded responses."""
        if self.replay_index >= len(self.recorded_responses):
            raise RuntimeError(
                f"Test tried to call LLM {self.replay_index + 1} times, "
                f"but only {len(self.recorded_responses)} responses were recorded. "
                f"Run with RECORD_MODE=true to re-record."
            )

        # Get next recorded response
        serialized = self.recorded_responses[self.replay_index]
        self.replay_index += 1

        # Deserialize and return as async generator
        return self._deserialize_response(serialized)

    def _serialize_response(self, response: LlmResponse) -> dict:
        """Convert LlmResponse to JSON-serializable dict."""
        content_dict = {
            "role": response.content.role if response.content else None,
            "parts": [],
        }

        if response.content and response.content.parts:
            for part in response.content.parts:
                part_dict = {}

                if part.text:
                    part_dict["text"] = part.text

                if part.function_call:
                    part_dict["function_call"] = {
                        "name": part.function_call.name,
                        "args": dict(part.function_call.args) if part.function_call.args else {},
                    }

                content_dict["parts"].append(part_dict)

        return {
            "content": content_dict,
            "finish_reason": response.finish_reason,
            "turn_complete": response.turn_complete,
        }

    async def _deserialize_response(self, serialized: dict):
        """Convert serialized dict back to LlmResponse and yield it."""
        # Reconstruct parts
        parts = []
        for part_dict in serialized["content"]["parts"]:
            if "text" in part_dict:
                parts.append(Part(text=part_dict["text"]))

            if "function_call" in part_dict:
                fc_dict = part_dict["function_call"]
                fc = FunctionCall(name=fc_dict["name"], args=fc_dict["args"])
                parts.append(Part(function_call=fc))

        # Reconstruct content
        content = Content(role=serialized["content"]["role"], parts=parts)

        # Create LlmResponse
        response = LlmResponse(
            content=content,
            finish_reason=serialized.get("finish_reason"),
            turn_complete=serialized.get("turn_complete", True),
        )

        yield response
