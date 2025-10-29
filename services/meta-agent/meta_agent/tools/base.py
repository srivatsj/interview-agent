"""Base interface for interview toolsets."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Iterable


class InterviewToolset(ABC):
    """Abstract base class for interview toolsets.

    Each toolset represents a specific interview type (e.g., system design, coding).
    """

    @classmethod
    @abstractmethod
    def get_interview_type(cls) -> str:
        """Return the interview type this toolset supports (e.g., 'system_design', 'coding')."""
        pass

    @abstractmethod
    def get_phases(self) -> list[dict[str, str]]:
        """Return the ordered list of interview phases."""
        pass

    @abstractmethod
    def get_context(self, phase_id: str) -> str:
        """Return context and guidance for a specific phase.

        Args:
            phase_id: The phase identifier

        Returns:
            Context string with phase guidance
        """
        pass

    @abstractmethod
    def get_question(self, candidate_info: dict[str, Any]) -> str:
        """Return an interview question based on candidate background.

        Args:
            candidate_info: Dictionary containing candidate details like
                          name, years_experience, domain, projects, etc.

        Returns:
            A contextual interview question tailored to the candidate
        """
        pass

    @abstractmethod
    def evaluate(
        self,
        phase_id: str,
        conversation_history: Iterable[dict[str, Any]],
    ) -> dict[str, Any]:
        """Evaluate candidate performance for a phase.

        Args:
            phase_id: The phase identifier
            conversation_history: List of conversation messages

        Returns:
            Evaluation results with decision, score, and feedback
        """
        pass
