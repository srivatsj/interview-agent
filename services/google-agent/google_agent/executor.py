"""Agent executor for the Google system design remote agent."""

from __future__ import annotations

import json
import logging
from typing import Any

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.types import Task, UnsupportedOperationError
from a2a.utils import new_agent_text_message
from a2a.utils.errors import ServerError

from .toolset import GoogleSystemDesignToolset

logger = logging.getLogger(__name__)


class GoogleAgentExecutor(AgentExecutor):
    """Deterministic executor that exposes system-design tooling as skills."""

    def __init__(self) -> None:
        self.toolset = GoogleSystemDesignToolset()

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Handle incoming requests by routing to the appropriate skill."""
        message_text = context.get_user_input()
        logger.debug("Received payload: %s", message_text)

        try:
            payload = json.loads(message_text or "{}")
        except json.JSONDecodeError as exc:
            logger.warning("Failed to decode payload: %s", exc)
            await event_queue.enqueue_event(
                new_agent_text_message(
                    self._serialize_error("invalid_json", "Provide valid JSON payload.")
                )
            )
            return

        result = self._dispatch(payload)
        await event_queue.enqueue_event(new_agent_text_message(result))

    async def cancel(
        self,
        request: RequestContext,
        event_queue: EventQueue,
    ) -> Task | None:
        raise ServerError(error=UnsupportedOperationError())

    def _dispatch(self, payload: dict[str, Any]) -> str:
        skill = payload.get("skill")
        args = payload.get("args", {}) or {}

        if not skill:
            return self._serialize_error("missing_skill", "Field 'skill' is required.")

        try:
            if skill == "get_phases":
                phases = self.toolset.get_phases()
                return self._serialize_ok(skill, {"phases": phases})

            if skill == "get_context":
                phase_id = args.get("phase_id")
                if not phase_id:
                    return self._serialize_error(
                        "missing_phase_id", "Field 'phase_id' is required for get_context."
                    )
                context_text = self.toolset.get_context(phase_id)
                return self._serialize_ok(skill, {"phase_id": phase_id, "context": context_text})

            if skill in {"evaluate_phase", "evaluate"}:
                phase_id = args.get("phase_id")
                history = args.get("conversation_history", [])
                if not phase_id:
                    return self._serialize_error(
                        "missing_phase_id",
                        "Field 'phase_id' is required for evaluate_phase.",
                    )
                if not isinstance(history, list):
                    return self._serialize_error(
                        "invalid_history",
                        "Field 'conversation_history' must be a list of messages.",
                    )
                evaluation = self.toolset.evaluate(phase_id, history)
                return self._serialize_ok(skill, {"phase_id": phase_id, "evaluation": evaluation})

            return self._serialize_error("unknown_skill", f"Unsupported skill '{skill}'.")
        except Exception as exc:
            logger.exception("Skill execution failed for %s", skill)
            return self._serialize_error("execution_error", str(exc))

    @staticmethod
    def _serialize_ok(skill: str, result: dict[str, Any]) -> str:
        response = {"status": "ok", "skill": skill, "result": result}
        return json.dumps(response, indent=2, sort_keys=True)

    @staticmethod
    def _serialize_error(code: str, message: str) -> str:
        response = {"status": "error", "error": {"code": code, "message": message}}
        return json.dumps(response, indent=2, sort_keys=True)
