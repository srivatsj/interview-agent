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

    # DEBUG: Print entire task structure
    logger.info(f"📦 Task ID: {task.id}")
    logger.info(f"📦 Task status: {task.status.state if task.status else 'None'}")
    has_msg = task.status.message is not None if task.status else False
    logger.info(f"📦 Has status.message: {has_msg}")
    logger.info(f"📦 Has artifacts: {task.artifacts is not None}")
    logger.info(f"📦 Has history: {task.history is not None}")

    if task.status and task.status.message:
        logger.info(f"📦 status.message.parts count: {len(task.status.message.parts)}")
        for i, part in enumerate(task.status.message.parts):
            logger.info(f"📦 status.message.parts[{i}].kind: {part.root.kind}")
            if part.root.kind == "text":
                text_preview = part.root.text[:200] if part.root.text else "None"
                logger.info(f"📦 status.message.parts[{i}].text: {text_preview}")
            if part.root.kind == "data":
                logger.info(f"📦 status.message.parts[{i}].data: {part.root.data}")

    if task.artifacts:
        logger.info(f"📦 artifacts count: {len(task.artifacts)}")
        for i, artifact in enumerate(task.artifacts):
            logger.info(f"📦 artifact[{i}].parts count: {len(artifact.parts)}")

    if task.history:
        logger.info(f"📦 history count: {len(task.history)}")
        for i, msg in enumerate(task.history):
            logger.info(f"📦 history[{i}].role: {msg.role}, parts: {len(msg.parts)}")
            for j, part in enumerate(msg.parts):
                logger.info(f"📦 history[{i}].parts[{j}].kind: {part.root.kind}")
                if part.root.kind == "data":
                    data_info = (
                        list(part.root.data.keys())
                        if isinstance(part.root.data, dict)
                        else type(part.root.data)
                    )
                    logger.info(f"📦 history[{i}].parts[{j}].data keys: {data_info}")

    # Extract response data
    result_data = {}

    # Check task.history for function responses (where ADK puts tool results)
    if task.history:
        for msg in task.history:
            for part in msg.parts:
                if part.root.kind == "data" and isinstance(part.root.data, dict):
                    # Check if this is a function response with 'response' key
                    if "response" in part.root.data:
                        response_value = part.root.data["response"]
                        if isinstance(response_value, dict):
                            result_data.update(response_value)
                            keys = list(response_value.keys())
                            logger.info(f"✅ Extracted from history function response: {keys}")

    # Check task status message (secondary location)
    if task.status and task.status.message:
        for part in task.status.message.parts:
            if part.root.kind == "text" and part.root.text:
                try:
                    parsed = json.loads(part.root.text)
                    if isinstance(parsed, dict):
                        result_data.update(parsed)
                        logger.info(f"✅ Extracted from status.message text: {list(parsed.keys())}")
                except (json.JSONDecodeError, ValueError):
                    pass

            if part.root.kind == "data" and part.root.data:
                if isinstance(part.root.data, dict):
                    result_data.update(part.root.data)
                    keys = list(part.root.data.keys())
                    logger.info(f"✅ Extracted from status.message data: {keys}")

    # Check task artifacts
    if task.artifacts:
        for artifact in task.artifacts:
            for part in artifact.parts:
                if part.root.kind == "text" and part.root.text:
                    try:
                        parsed = json.loads(part.root.text)
                        if isinstance(parsed, dict):
                            result_data.update(parsed)
                            logger.info(f"✅ Extracted from artifacts text: {list(parsed.keys())}")
                    except (json.JSONDecodeError, ValueError):
                        pass

                if part.root.kind == "data" and part.root.data:
                    if isinstance(part.root.data, dict):
                        result_data.update(part.root.data)
                        keys = list(part.root.data.keys())
                        logger.info(f"✅ Extracted from artifacts data: {keys}")

    if not result_data:
        logger.error("❌ No data extracted from remote agent response")

    return result_data
