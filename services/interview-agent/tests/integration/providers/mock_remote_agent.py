"""Mock responses for A2A remote agent testing."""

import json


class MockA2AResponses:
    """Collection of mock A2A responses for remote agent testing."""

    @staticmethod
    def wrap_a2a_response(payload: dict) -> dict:
        """Wrap payload in A2A response format."""
        return {"content": json.dumps(payload)}

    @staticmethod
    def get_supported_interview_types():
        """Mock response for get_supported_interview_types skill."""
        return MockA2AResponses.wrap_a2a_response(
            {
                "status": "ok",
                "skill": "get_supported_interview_types",
                "result": {"interview_types": ["system_design"]},
            }
        )

    @staticmethod
    def start_interview():
        """Mock response for start_interview skill."""
        return MockA2AResponses.wrap_a2a_response(
            {
                "status": "ok",
                "skill": "start_interview",
                "result": {
                    "interview_type": "system_design",
                    "candidate_info": {"name": "Jane Doe", "years_experience": 5},
                    "message": "Interview session started for system_design",
                },
            }
        )

    @staticmethod
    def get_phases():
        """Mock response for get_phases skill."""
        return MockA2AResponses.wrap_a2a_response(
            {
                "status": "ok",
                "skill": "get_phases",
                "result": {
                    "phases": [
                        {"id": "plan_and_scope", "name": "Plan & High-Level Scope"},
                        {"id": "requirements_alignment", "name": "Requirements Alignment"},
                        {"id": "architecture_blueprint", "name": "Architecture Blueprint"},
                    ]
                },
            }
        )

    @staticmethod
    def get_context():
        """Mock response for get_context skill."""
        return MockA2AResponses.wrap_a2a_response(
            {
                "status": "ok",
                "skill": "get_context",
                "result": {
                    "phase_id": "plan_and_scope",
                    "context": (
                        "Begin by aligning on the interview plan and system's high-level outline."
                    ),
                },
            }
        )

    @staticmethod
    def get_question():
        """Mock response for get_question skill."""
        return MockA2AResponses.wrap_a2a_response(
            {
                "status": "ok",
                "skill": "get_question",
                "result": {
                    "question": "Given your 5 years of experience in distributed systems, "
                    "design a URL shortening service like bit.ly."
                },
            }
        )

    @staticmethod
    def evaluate_phase_continue():
        """Mock response for evaluate_phase skill (continue decision)."""
        return MockA2AResponses.wrap_a2a_response(
            {
                "status": "ok",
                "skill": "evaluate_phase",
                "result": {
                    "phase_id": "plan_and_scope",
                    "evaluation": {
                        "decision": "continue",
                        "score": 4,
                        "gaps": ["architecture", "component"],
                        "followup_questions": "Expand on: architecture, component",
                    },
                },
            }
        )

    @staticmethod
    def evaluate_phase_next():
        """Mock response for evaluate_phase skill (next_phase decision)."""
        return MockA2AResponses.wrap_a2a_response(
            {
                "status": "ok",
                "skill": "evaluate_phase",
                "result": {
                    "phase_id": "plan_and_scope",
                    "evaluation": {
                        "decision": "next_phase",
                        "score": 8,
                        "message": "Phase objectives satisfied, proceed.",
                    },
                },
            }
        )

    @staticmethod
    def error_response(code: str = "unknown_error", message: str = "An error occurred"):
        """Mock error response."""
        return MockA2AResponses.wrap_a2a_response(
            {"status": "error", "error": {"code": code, "message": message}}
        )
