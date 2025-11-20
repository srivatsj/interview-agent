"""A2A client for calling remote interview agents."""

import json
import logging
import uuid
from typing import Any

import httpx
from a2a.client.card_resolver import A2ACardResolver
from a2a.client.client import Client, ClientConfig
from a2a.client.client_factory import ClientFactory
from a2a.client.client_task_manager import ClientTaskManager
from a2a.types import DataPart, Message, Part, Role, Task, TextPart


class RemoteAgentClient:
    """Client for calling remote agents via A2A protocol."""

    def __init__(self, base_url: str, timeout: float = 60.0):
        """Initialize client.

        Args:
            base_url: Base URL of remote agent (e.g., http://localhost:10123)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url
        self.httpx_client = httpx.AsyncClient(timeout=httpx.Timeout(timeout))
        self.client_factory = ClientFactory(ClientConfig(httpx_client=self.httpx_client))
        self._agent_card = None
        self._a2a_client = None

    async def get_agent_card(self):
        """Fetch agent card from remote agent."""
        if self._agent_card is None:
            resolver = A2ACardResolver(httpx_client=self.httpx_client, base_url=self.base_url)
            self._agent_card = await resolver.get_agent_card()
        return self._agent_card

    async def _get_client(self) -> Client:
        """Get or create A2A client."""
        if self._a2a_client is None:
            agent_card = await self.get_agent_card()
            self._a2a_client = self.client_factory.create(agent_card)
        return self._a2a_client

    async def send_message(
        self,
        text: str,
        data: dict[str, Any] | None = None,
        context_id: str | None = None,
    ) -> Task:
        """Send A2A message to remote agent.

        Args:
            text: Text message to send
            data: Optional data dictionary to include
            context_id: Optional A2A context ID for conversation continuity

        Returns:
            A2A Task response from remote agent
        """
        # Build message parts
        parts = [Part(root=TextPart(text=text))]
        if data:
            parts.append(Part(root=DataPart(data=data)))

        # Create message
        message = Message(
            message_id=uuid.uuid4().hex,
            parts=parts,
            role=Role.agent,
            context_id=context_id,
        )

        # Send and collect response
        client = await self._get_client()
        task_manager = ClientTaskManager()

        async for event in client.send_message(message):
            if isinstance(event, tuple):
                event = event[0]
            await task_manager.process(event)

        task = task_manager.get_task()
        if task is None:
            raise RuntimeError(f"No response from {self.base_url}")

        return task


async def call_remote_skill(
    agent_url: str,
    text: str,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Convenience function to call remote agent skill.

    Args:
        agent_url: Remote agent URL
        text: Text instruction
        data: Optional data to pass

    Returns:
        Response data from remote agent

    Example:
        cart = await call_remote_skill(
            "http://localhost:10123",
            "Create cart for system design interview",
            {"interview_type": "system_design"}
        )
    """
    logger = logging.getLogger(__name__)

    client = RemoteAgentClient(agent_url)
    task = await client.send_message(text, data)

    # Extract tool response from task history
    # ADK stores function responses in task.history with metadata adk_type='function_response'
    result_data = {}

    for message in task.history or []:
        for part in message.parts:
            # Check for TextPart with JSON response
            if hasattr(part.root, "text") and part.root.text:
                try:
                    parsed = json.loads(part.root.text)
                    if isinstance(parsed, dict):
                        result_data.update(parsed)
                        keys = list(parsed.keys())
                        logger.debug(f"Parsed text response from remote agent: {keys}")
                except (json.JSONDecodeError, ValueError):
                    pass  # Not JSON, skip

            # Check for function response in DataPart
            if hasattr(part.root, "data") and part.root.data:
                metadata = getattr(part, "metadata", None) or getattr(part.root, "metadata", None)

                # ADK function responses have metadata.adk_type == 'function_response'
                if metadata and metadata.get("adk_type") == "function_response":
                    response_data = part.root.data.get("response", {})
                    result_str = response_data.get("result", "")

                    # Parse JSON result
                    if result_str:
                        try:
                            parsed = json.loads(result_str)
                            if isinstance(parsed, dict):
                                result_data.update(parsed)
                                logger.debug("Parsed function response from remote agent")
                        except (json.JSONDecodeError, ValueError) as e:
                            logger.warning(f"Failed to parse function response JSON: {e}")

    if not result_data:
        history_len = len(task.history or [])
        logger.warning(
            f"No data extracted from remote agent response. Task history: {history_len} messages"
        )

    return result_data
