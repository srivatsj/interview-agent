"""WebSocket test client for orchestrator E2E tests."""

import asyncio
import json
import logging
from typing import AsyncGenerator, Optional

import websockets

logger = logging.getLogger(__name__)


class WebSocketTestClient:
    """Test client for orchestrator WebSocket communication."""

    def __init__(self, user_id: str, interview_id: str, base_url: str = "ws://localhost:8000"):
        self.user_id = user_id
        self.interview_id = interview_id
        self.url = f"{base_url}/ws/{user_id}?interview_id={interview_id}&is_audio=false"
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self.messages: list[dict] = []

    async def connect(self):
        """Connect to orchestrator WebSocket."""
        logger.info(f"🔌 Connecting to {self.url}")
        self.ws = await websockets.connect(self.url)
        logger.info("✅ WebSocket connected")

    async def send_text(self, message: str):
        """Send text message to orchestrator."""
        if not self.ws:
            raise RuntimeError("WebSocket not connected")

        payload = {"mime_type": "text/plain", "data": message}
        await self.ws.send(json.dumps(payload))
        logger.debug(f"📤 Sent: {message[:50]}...")

    async def send_canvas_image(self, image_base64: str):
        """Send canvas screenshot (PNG) to orchestrator.

        Simulates frontend sending periodic canvas updates.
        """
        if not self.ws:
            raise RuntimeError("WebSocket not connected")

        payload = {"mime_type": "image/png", "data": image_base64}
        await self.ws.send(json.dumps(payload))
        logger.info(f"📷 Sent canvas screenshot ({len(image_base64)} bytes)")

    async def receive_messages(self, timeout: float = 30.0) -> AsyncGenerator[dict, None]:
        """Receive messages from orchestrator."""
        if not self.ws:
            raise RuntimeError("WebSocket not connected")

        while True:
            try:
                message = await asyncio.wait_for(self.ws.recv(), timeout=timeout)
                data = json.loads(message)
                self.messages.append(data)
                logger.debug(f"📥 Received: {data.get('type', 'unknown')}")
                yield data
            except asyncio.TimeoutError:
                logger.debug("⏱️  Receive timeout - no more messages")
                break
            except websockets.exceptions.ConnectionClosed:
                logger.warning("⚠️  WebSocket connection closed")
                break

    async def send_and_wait(
        self, message: str, wait_for_complete: bool = True, timeout: float = 30.0
    ) -> list[dict]:
        """Send message and wait for complete response.

        Args:
            message: Text message to send
            wait_for_complete: Wait for turn_complete event
            timeout: Max time to wait for response

        Returns:
            List of response messages
        """
        await self.send_text(message)

        responses = []
        async for msg in self.receive_messages(timeout=timeout):
            responses.append(msg)
            # Check for turn_complete in the message structure
            if wait_for_complete and msg.get("turn_complete"):
                break

        logger.info(f"✅ Received {len(responses)} messages")
        return responses

    async def close(self):
        """Close WebSocket connection."""
        if self.ws:
            logger.info("🔌 Closing WebSocket connection")
            await self.ws.close()
            self.ws = None

    def get_text_responses(self) -> str:
        """Extract all text content from received messages."""
        text_parts = []
        for msg in self.messages:
            # Check parts array for text content
            if "parts" in msg:
                for part in msg["parts"]:
                    if part.get("type") == "text" and part.get("data"):
                        text_parts.append(part["data"])
            # Also check output_transcription
            if "output_transcription" in msg and msg["output_transcription"]:
                if isinstance(msg["output_transcription"], dict):
                    text = msg["output_transcription"].get("text")
                    if text:
                        text_parts.append(text)
        return "".join(text_parts)

    def get_messages_by_author(self, author: str) -> list[dict]:
        """Get all messages from specific author."""
        return [m for m in self.messages if m.get("author") == author]
