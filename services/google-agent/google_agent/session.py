"""Session state management for interviews."""

from __future__ import annotations

from typing import Any


class InterviewSession:
    """Session state for a single interview context."""

    def __init__(self, interview_type: str, candidate_info: dict[str, Any]) -> None:
        """Initialize interview session.

        Args:
            interview_type: Type of interview (e.g., 'system_design', 'coding')
            candidate_info: Candidate details (name, years_experience, domain, projects)
        """
        self.interview_type = interview_type
        self.candidate_info = candidate_info
        self.conversation_history: list[dict[str, Any]] = []
        self.current_phase_index = 0
