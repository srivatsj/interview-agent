"""Helper functions for A2A client communication."""

import uuid
from typing import Any

import httpx
from a2a.client.card_resolver import A2ACardResolver
from a2a.client.client import ClientConfig
from a2a.client.client_factory import ClientFactory
from a2a.client.client_task_manager import ClientTaskManager
from a2a.types import DataPart, Message, Part, Role, TextPart


async def send_a2a_message(
    agent_url: str,
    text: str,
    data: dict[str, Any] | None = None,
    timeout: float = 60.0,
) -> dict[str, Any]:
    """Send A2A message to agent and return response data.

    Args:
        agent_url: URL of the agent server
        text: Text message to send
        data: Optional data dictionary
        timeout: Request timeout in seconds

    Returns:
        Response data dictionary from agent
    """
    async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as httpx_client:
        # Get agent card
        resolver = A2ACardResolver(httpx_client=httpx_client, base_url=agent_url)
        agent_card = await resolver.get_agent_card()

        # Create client
        factory = ClientFactory(ClientConfig(httpx_client=httpx_client))
        client = factory.create(agent_card)

        # Build message
        parts = [Part(root=TextPart(text=text))]
        if data:
            parts.append(Part(root=DataPart(data=data)))

        message = Message(
            message_id=uuid.uuid4().hex,
            parts=parts,
            role=Role.agent,
        )

        # Send and collect response
        task_manager = ClientTaskManager()
        async for event in client.send_message(message):
            if isinstance(event, tuple):
                event = event[0]
            await task_manager.process(event)

        task = task_manager.get_task()
        if not task:
            raise RuntimeError(f"No task from {agent_url}")

        # Try to extract data from artifacts first
        if task.artifacts:
            for artifact in task.artifacts:
                for part in artifact.parts:
                    if part.root.kind == "data" and isinstance(part.root.data, dict):
                        return part.root.data

        # Fallback: check status message
        if task.status and task.status.message and task.status.message.parts:
            text_content = (
                task.status.message.parts[0].root.text
                if hasattr(task.status.message.parts[0].root, "text")
                else None
            )
            if text_content:
                return {"message": text_content}

        # Last resort: return empty response with task status
        return {"status": task.status.state.value if task.status else "unknown"}
