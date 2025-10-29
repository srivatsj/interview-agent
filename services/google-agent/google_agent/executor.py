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
from google.adk.events import Event, EventActions
from google.adk.sessions import InMemorySessionService, Session

from .tools.base import InterviewToolset
from .tools.coding_toolset import CodingToolset
from .tools.design_toolset import GoogleSystemDesignToolset

logger = logging.getLogger(__name__)


class GoogleAgentExecutor(AgentExecutor):
    """Deterministic executor exposing interview tooling as skills with ADK session management."""

    def __init__(self, toolsets: list[type[InterviewToolset]] | None = None) -> None:
        """Initialize executor with optional list of toolset classes.

        Args:
            toolsets: List of InterviewToolset classes to support.
                     Defaults to [GoogleSystemDesignToolset, CodingToolset]
        """
        # Register toolsets (default to all available)
        if toolsets is None:
            toolsets = [GoogleSystemDesignToolset, CodingToolset]

        # Map interview_type -> toolset instance
        self.toolsets: dict[str, InterviewToolset] = {}
        for toolset_cls in toolsets:
            instance = toolset_cls()
            interview_type = toolset_cls.get_interview_type()
            self.toolsets[interview_type] = instance

        # Use ADK's session service for state management (no LLM needed)
        self.session_service = InMemorySessionService()
        self._app_name = "google_interview_agent"
        self._user_id = "interview_system"

    async def _get_or_create_session(self, context_id: str) -> Session:
        """Get or create an ADK session using A2A's context_id as session_id."""
        session = await self.session_service.get_session(
            app_name=self._app_name,
            user_id=self._user_id,
            session_id=context_id,
        )
        if session is None:
            session = await self.session_service.create_session(
                app_name=self._app_name,
                user_id=self._user_id,
                session_id=context_id,
                state={},
            )
        return session

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        """Handle incoming requests by routing to the appropriate skill."""
        message_text = context.get_user_input()
        context_id = context.context_id
        logger.debug("Received payload: %s for context_id: %s", message_text, context_id)

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

        # Get or create session
        session = await self._get_or_create_session(context_id)

        result = await self._dispatch(payload, session)
        await event_queue.enqueue_event(new_agent_text_message(result))

    async def cancel(
        self,
        request: RequestContext,
        event_queue: EventQueue,
    ) -> Task | None:
        raise ServerError(error=UnsupportedOperationError())

    async def _update_session_state(self, session: Session, state_delta: dict[str, Any]) -> None:
        """Update session state using ADK's event system."""
        import time

        event = Event(
            invocation_id=f"state_update_{time.time()}",
            author="system",
            actions=EventActions(state_delta=state_delta),
            timestamp=time.time(),
        )
        await self.session_service.append_event(session, event)

    async def _dispatch(self, payload: dict[str, Any], session: Session) -> str:
        skill = payload.get("skill")
        args = payload.get("args", {}) or {}

        if not skill:
            return self._serialize_error("missing_skill", "Field 'skill' is required.")

        try:
            # Discovery skill - no session state required
            if skill == "get_supported_interview_types":
                types = list(self.toolsets.keys())
                return self._serialize_ok(skill, {"interview_types": types})

            # Start interview - initializes session state
            if skill == "start_interview":
                interview_type = args.get("interview_type")
                candidate_info = args.get("candidate_info", {})

                if not interview_type:
                    return self._serialize_error(
                        "missing_interview_type",
                        "Field 'interview_type' is required for start_interview.",
                    )

                # Validate interview type
                if interview_type not in self.toolsets:
                    supported = list(self.toolsets.keys())
                    return self._serialize_error(
                        "unsupported_interview_type",
                        f"Interview type '{interview_type}' not supported. "
                        f"Supported: {', '.join(supported)}",
                    )

                # Update session state via ADK
                await self._update_session_state(
                    session,
                    {
                        "interview_type": interview_type,
                        "candidate_info": candidate_info,
                        "conversation_history": [],
                    },
                )

                logger.info(
                    "Started %s interview for session %s with candidate: %s",
                    interview_type,
                    session.id,
                    candidate_info.get("name", "Unknown"),
                )

                return self._serialize_ok(
                    skill,
                    {
                        "interview_type": interview_type,
                        "candidate_info": candidate_info,
                        "message": f"Interview session started for {interview_type}",
                    },
                )

            # All other skills require an active session
            if "interview_type" not in session.state:
                return self._serialize_error(
                    "no_session",
                    f"No active interview session for session {session.id}. "
                    "Call start_interview first.",
                )

            # Get the appropriate toolset based on interview type from session
            interview_type = session.state.get("interview_type")
            if not interview_type:
                return self._serialize_error(
                    "no_session",
                    "Internal error: interview_type not in session state.",
                )

            toolset = self.toolsets.get(interview_type)
            if not toolset:
                return self._serialize_error(
                    "invalid_interview_type",
                    f"No toolset registered for interview type '{interview_type}'.",
                )

            if skill == "get_phases":
                phases = toolset.get_phases()
                return self._serialize_ok(skill, {"phases": phases})

            if skill == "get_context":
                phase_id = args.get("phase_id")
                if not phase_id:
                    return self._serialize_error(
                        "missing_phase_id", "Field 'phase_id' is required for get_context."
                    )
                context_text = toolset.get_context(phase_id)
                return self._serialize_ok(skill, {"phase_id": phase_id, "context": context_text})

            if skill == "get_question":
                # Get candidate info from session state
                candidate_info = session.state.get("candidate_info", {})
                question = toolset.get_question(candidate_info)
                return self._serialize_ok(skill, {"question": question})

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

                # Update session conversation history
                await self._update_session_state(session, {"conversation_history": history})

                evaluation = toolset.evaluate(phase_id, history)
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
