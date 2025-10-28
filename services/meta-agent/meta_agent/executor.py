"""Agent executor for the LangGraph system design agent."""

from __future__ import annotations

import json
import logging
from typing import Any

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import Task, UnsupportedOperationError
from a2a.utils import new_agent_text_message
from a2a.utils.errors import ServerError

from meta_agent.agent import MetaAgent

logger = logging.getLogger(__name__)


class MetaAgentExecutor(AgentExecutor):
    """Deterministic executor that routes skill payloads through LangGraph."""

    def __init__(self) -> None:
        self.agent = MetaAgent()

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Handle incoming requests and enqueue the agent's JSON response."""
        raw_input = context.get_user_input() or ""
        logger.debug("Received payload: %s", raw_input)

        try:
            response = self.agent.dispatch(raw_input)
        except Exception as exc:  # pragma: no cover - defensive fallback
            logger.exception("LangGraph dispatch failure")
            response = self._serialize_error("execution_error", str(exc))

        await event_queue.enqueue_event(new_agent_text_message(response))

    async def cancel(
        self,
        request: RequestContext,
        event_queue: EventQueue,
    ) -> Task | None:
        raise ServerError(error=UnsupportedOperationError())

    @staticmethod
    def _serialize_error(code: str, message: str) -> str:
        payload: dict[str, Any] = {
            "status": "error",
            "error": {"code": code, "message": message},
        }
        # Keep output formatting consistent with the deterministic dispatch.
        return json.dumps(payload, indent=2, sort_keys=True)
