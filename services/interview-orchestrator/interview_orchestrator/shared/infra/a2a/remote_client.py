"""A2A client for calling remote interview agents - SIMPLIFIED."""

import logging
import uuid
from typing import Any

import httpx
from a2a.client.card_resolver import A2ACardResolver
from a2a.client.client import Client, ClientConfig
from a2a.client.client_factory import ClientFactory
from a2a.client.client_task_manager import ClientTaskManager
from a2a.types import DataPart, Message, Part, Role, Task, TextPart

logger = logging.getLogger(__name__)


class RemoteAgentClient:
    """Client for calling remote agents via A2A protocol."""

    def __init__(self, base_url: str, timeout: float = 60.0):
        """Initialize client.

        Args:
            base_url: Base URL of remote agent
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
        task_id: str | None = None,
    ) -> Task:
        """Send A2A message and return task.

        Args:
            text: Text command
            data: Optional data dictionary
            context_id: Optional context ID for multi-turn
            task_id: Optional task ID to continue existing task

        Returns:
            A2A Task response
        """
        parts = [Part(root=TextPart(text=text))]
        if data:
            parts.append(Part(root=DataPart(data=data)))

        message = Message(
            message_id=uuid.uuid4().hex,
            parts=parts,
            role=Role.agent,
            context_id=context_id,
            task_id=task_id,
        )

        client = await self._get_client()
        task_manager = ClientTaskManager()

        logger.info(f"📤 Sending message to {self.base_url}...")
        event_count = 0
        async for event in client.send_message(message):
            if isinstance(event, tuple):
                event = event[0]
            event_count += 1
            logger.info(f"📨 Event #{event_count}: {type(event).__name__}")
            await task_manager.process(event)

        logger.info(f"✅ Received {event_count} events, extracting task...")
        task = task_manager.get_task()
        if task is None:
            raise RuntimeError(f"No response from {self.base_url}")

        return task


async def call_remote_skill(
    agent_url: str,
    text: str,
    data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Call remote agent skill - SIMPLIFIED.

    With custom executor, response is ALWAYS in task.artifacts as DataPart.

    Args:
        agent_url: Remote agent URL
        text: Text command
        data: Optional data dictionary

    Returns:
        Response data from artifacts

    Raises:
        RuntimeError: If no data found in response
    """
    client = RemoteAgentClient(agent_url)
    task = await client.send_message(text, data)

    return extract_data_from_task(task)


def extract_data_from_task(task: Task) -> dict[str, Any]:
    """Extract data from task artifacts.

    Simple, clean extraction - custom executor always puts data in artifacts.

    Args:
        task: A2A Task response

    Returns:
        Data dictionary from first DataPart in artifacts

    Raises:
        RuntimeError: If no data found
    """
    logger.info(
        f"🔍 Extracting data from task (status: {task.status.state if task.status else 'NO_STATUS'})"
    )

    if not task.artifacts:
        logger.error(f"❌ No artifacts in response (task_id: {task.task_id})")
        logger.error(f"📋 Task status message: {task.status.message if task.status else 'NONE'}")
        raise RuntimeError("No artifacts in task response")

    logger.info(f"📦 Found {len(task.artifacts)} artifact(s)")

    for i, artifact in enumerate(task.artifacts):
        logger.info(f"📦 Artifact #{i + 1}: {len(artifact.parts)} part(s)")
        for j, part in enumerate(artifact.parts):
            logger.info(f"  Part #{j + 1}: kind={part.root.kind}, type={type(part.root).__name__}")
            if part.root.kind == "data" and isinstance(part.root.data, dict):
                data_keys = list(part.root.data.keys())
                logger.info(f"✅ Extracted data with keys: {data_keys}")
                if "message" in part.root.data:
                    logger.info(f"📝 Message preview: {part.root.data['message'][:200]}...")
                return part.root.data

    logger.error("❌ No data found in artifacts")
    raise RuntimeError("No DataPart found in task artifacts")
