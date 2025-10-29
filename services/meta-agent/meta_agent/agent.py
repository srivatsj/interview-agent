import json
from typing import Any, TypedDict

from langgraph.constants import END
from langgraph.graph import StateGraph

from meta_agent.session import InterviewSession
from meta_agent.tools.design_toolset import MetaAgentToolset


class MetaAgentState(TypedDict, total=False):
    raw_input: str
    payload: dict[str, Any]
    skill: str
    args: dict[str, Any]
    result: dict[str, Any]
    error_info: dict[str, str]
    message: str
    context_id: str
    sessions: dict[str, Any]  # Will hold the sessions dict from executor


class MetaAgent:
    """LangGraph agent exposing Meta-style deterministic interview skills."""

    SUPPORTED_CONTENT_TYPES = ["text"]

    def __init__(self) -> None:
        self.toolset = MetaAgentToolset()
        self.graph = self._build_graph()

    def _build_graph(self):
        builder = StateGraph(MetaAgentState)
        builder.add_node("parse", self._parse_payload)
        builder.add_node(
            "get_supported_interview_types", self._handle_get_supported_interview_types
        )
        builder.add_node("start_interview", self._handle_start_interview)
        builder.add_node("get_phases", self._handle_get_phases)
        builder.add_node("get_context", self._handle_get_context)
        builder.add_node("get_question", self._handle_get_question)
        builder.add_node("evaluate", self._handle_evaluate)
        builder.add_node("error", self._handle_error)
        builder.add_node("serialize", self._serialize_response)

        builder.set_entry_point("parse")
        builder.add_conditional_edges(
            "parse",
            self._route_from_parse,
            {
                "error": "error",
                "get_supported_interview_types": "get_supported_interview_types",
                "start_interview": "start_interview",
                "get_phases": "get_phases",
                "get_context": "get_context",
                "get_question": "get_question",
                "evaluate": "evaluate",
            },
        )
        builder.add_edge("get_supported_interview_types", "serialize")
        builder.add_edge("start_interview", "serialize")
        builder.add_edge("get_phases", "serialize")
        builder.add_edge("get_context", "serialize")
        builder.add_edge("get_question", "serialize")
        builder.add_edge("evaluate", "serialize")
        builder.add_edge("error", "serialize")
        builder.add_edge("serialize", END)

        return builder.compile()

    def dispatch(self, raw_input: str, context_id: str, sessions: dict[str, Any]) -> str:
        """Run the LangGraph state machine and return the JSON response string."""
        final_state = self.graph.invoke(
            {
                "raw_input": raw_input or "",
                "context_id": context_id,
                "sessions": sessions,
            }
        )
        message = final_state.get("message")
        if isinstance(message, str):
            return message
        return json.dumps(
            {
                "status": "error",
                "error": {
                    "code": "dispatch_failure",
                    "message": "Unable to serialize response.",
                },
            },
            indent=2,
            sort_keys=True,
        )

    def _parse_payload(self, state: MetaAgentState) -> MetaAgentState:
        raw = state.get("raw_input") or ""
        try:
            payload = json.loads(raw or "{}")
        except json.JSONDecodeError:
            state["error_info"] = {
                "code": "invalid_json",
                "message": "Provide a valid JSON payload.",
            }
            return state

        if not isinstance(payload, dict):
            state["error_info"] = {
                "code": "invalid_payload",
                "message": "Payload must be a JSON object.",
            }
            return state

        skill = payload.get("skill")
        if not skill:
            state["error_info"] = {
                "code": "missing_skill",
                "message": "Field 'skill' is required.",
            }
            return state

        state["payload"] = payload
        state["skill"] = str(skill)
        args = payload.get("args", {}) or {}
        if not isinstance(args, dict):
            state["error_info"] = {
                "code": "invalid_args",
                "message": "Field 'args' must be an object when provided.",
            }
            return state
        state["args"] = args
        return state

    def _route_from_parse(self, state: MetaAgentState) -> str:
        if state.get("error_info"):
            return "error"
        skill = state.get("skill", "")

        # Discovery skill - no session required
        if skill == "get_supported_interview_types":
            return "get_supported_interview_types"

        # Start interview - creates session
        if skill == "start_interview":
            return "start_interview"

        # All other skills require an active session
        context_id = state.get("context_id", "")
        sessions = state.get("sessions", {})
        if skill not in {"get_supported_interview_types", "start_interview"}:
            if context_id not in sessions:
                state["error_info"] = {
                    "code": "no_session",
                    "message": f"No active interview session for context {context_id}. "
                    "Call start_interview first.",
                }
                return "error"

        if skill == "get_phases":
            return "get_phases"
        if skill == "get_context":
            return "get_context"
        if skill == "get_question":
            return "get_question"
        if skill in {"evaluate_phase", "evaluate"}:
            return "evaluate"

        state["error_info"] = {
            "code": "unknown_skill",
            "message": f"Unsupported skill '{skill}'.",
        }
        return "error"

    def _handle_get_supported_interview_types(self, state: MetaAgentState) -> MetaAgentState:
        interview_type = self.toolset.get_interview_type()
        state["result"] = {
            "skill": state.get("skill"),
            "result": {"interview_types": [interview_type]},
        }
        return state

    def _handle_start_interview(self, state: MetaAgentState) -> MetaAgentState:
        args = state.get("args", {})
        interview_type = args.get("interview_type")
        candidate_info = args.get("candidate_info", {})
        context_id = state.get("context_id", "")
        sessions = state.get("sessions", {})

        if not interview_type:
            state["error_info"] = {
                "code": "missing_interview_type",
                "message": "Field 'interview_type' is required for start_interview.",
            }
            return state

        # Validate interview type
        supported_type = self.toolset.get_interview_type()
        if interview_type != supported_type:
            state["error_info"] = {
                "code": "unsupported_interview_type",
                "message": f"Interview type '{interview_type}' not supported. "
                f"Supported: {supported_type}",
            }
            return state

        # Create or reset session
        sessions[context_id] = InterviewSession(interview_type, candidate_info)

        state["result"] = {
            "skill": state.get("skill"),
            "result": {
                "interview_type": interview_type,
                "candidate_info": candidate_info,
                "message": f"Interview session started for {interview_type}",
            },
        }
        return state

    def _handle_get_phases(self, state: MetaAgentState) -> MetaAgentState:
        phases = self.toolset.get_phases()
        state["result"] = {"skill": state.get("skill"), "result": {"phases": phases}}
        return state

    def _handle_get_context(self, state: MetaAgentState) -> MetaAgentState:
        args = state.get("args", {})
        phase_id = args.get("phase_id")
        if not phase_id:
            state["error_info"] = {
                "code": "missing_phase_id",
                "message": "Field 'phase_id' is required for get_context.",
            }
            return state
        context_text = self.toolset.get_context(str(phase_id))
        state["result"] = {
            "skill": state.get("skill"),
            "result": {"phase_id": phase_id, "context": context_text},
        }
        return state

    def _handle_get_question(self, state: MetaAgentState) -> MetaAgentState:
        # Get candidate info from session
        context_id = state.get("context_id", "")
        sessions = state.get("sessions", {})
        session = sessions.get(context_id)

        if not session:
            state["error_info"] = {
                "code": "no_session",
                "message": "No active session found. Call start_interview first.",
            }
            return state

        candidate_info = session.candidate_info if hasattr(session, "candidate_info") else {}
        question = self.toolset.get_question(candidate_info)
        state["result"] = {
            "skill": state.get("skill"),
            "result": {"question": question},
        }
        return state

    def _handle_evaluate(self, state: MetaAgentState) -> MetaAgentState:
        args = state.get("args", {})
        phase_id = args.get("phase_id")
        conversation_history = args.get("conversation_history", [])

        if not phase_id:
            state["error_info"] = {
                "code": "missing_phase_id",
                "message": "Field 'phase_id' is required for evaluate_phase.",
            }
            return state

        if not isinstance(conversation_history, list):
            state["error_info"] = {
                "code": "invalid_history",
                "message": "Field 'conversation_history' must be a list of messages.",
            }
            return state

        evaluation = self.toolset.evaluate(str(phase_id), conversation_history)
        state["result"] = {
            "skill": state.get("skill"),
            "result": {"phase_id": phase_id, "evaluation": evaluation},
        }
        return state

    def _handle_error(self, state: MetaAgentState) -> MetaAgentState:
        return state

    def _serialize_response(self, state: MetaAgentState) -> MetaAgentState:
        if state.get("error_info"):
            response = {"status": "error", "error": state["error_info"]}
        else:
            result = state.get("result", {})
            response = {
                "status": "ok",
                "skill": result.get("skill"),
                "result": result.get("result"),
            }
        state["message"] = json.dumps(response, indent=2, sort_keys=True)
        return state
