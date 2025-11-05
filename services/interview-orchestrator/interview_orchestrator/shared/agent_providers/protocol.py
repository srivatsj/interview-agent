"""Protocol defining the interface for interview agent providers.

This protocol defines the contract that both local and remote interview agents must implement.
Uses Python's typing.Protocol for structural subtyping (duck typing with type safety).
"""

from typing import Any, Protocol


class InterviewAgentProtocol(Protocol):
    """Protocol for interview agent providers (local or remote).

    This protocol defines the required interface for all interview agents,
    whether they are local tool providers or remote A2A agents.

    All methods must be implemented by conforming classes.
    """

    async def start_interview(
        self, interview_type: str, candidate_info: dict[str, Any]
    ) -> dict[str, Any]:
        """Start an interview session.

        Args:
            interview_type: Type of interview (e.g., 'system_design', 'coding')
            candidate_info: Candidate background information

        Returns:
            Response with session information
        """
        ...

    async def get_question(self) -> str:
        """Get an interview question tailored to candidate background.

        Returns:
            Interview question
        """
        ...

    async def get_phases(self) -> list[dict[str, str]]:
        """Get interview phases in order.

        Returns:
            List of phases with 'id' and 'name' keys
        """
        ...

    async def get_context(self, phase_id: str) -> str:
        """Get context/guidance for a specific phase.

        Args:
            phase_id: Phase identifier

        Returns:
            Context string describing what to discuss in this phase
        """
        ...

    async def evaluate_phase(
        self, phase_id: str, conversation_history: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Evaluate phase completion based on conversation history.

        Args:
            phase_id: Phase identifier
            conversation_history: List of conversation messages

        Returns:
            Evaluation result with 'decision', 'score', and optional 'gaps'/'message'
            - decision: 'continue' or 'next_phase'
            - score: Integer score (typically 0-10)
            - gaps: List of missing topics (when decision='continue')
            - message: Optional feedback message
        """
        ...
