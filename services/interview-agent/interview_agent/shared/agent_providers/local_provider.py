"""Local agent provider wrapper for local tool implementations.

Wraps local tool providers (e.g., DefaultSystemDesignTools) to match the
InterviewAgentProtocol interface, providing consistency with remote agents.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


class LocalAgentProvider:
    """Local wrapper for local tool providers.

    Adapts local tool providers to match the InterviewAgentProtocol interface,
    allowing them to be used interchangeably with RemoteAgentProvider instances.
    """

    def __init__(self, tool_provider: Any):
        """Initialize local agent provider.

        Args:
            tool_provider: Local tool provider instance (e.g., DefaultSystemDesignTools)
        """
        self._provider = tool_provider
        self._candidate_info: dict[str, Any] = {}
        self._interview_type: str = ""

    async def start_interview(
        self, interview_type: str, candidate_info: dict[str, Any]
    ) -> dict[str, Any]:
        """Start an interview session (local no-op).

        For local providers, this just stores the session info.

        Args:
            interview_type: Type of interview
            candidate_info: Candidate background information

        Returns:
            Success response
        """
        self._interview_type = interview_type
        self._candidate_info = candidate_info

        # Pass candidate info to underlying provider if it has _candidate_info attribute
        if hasattr(self._provider, "_candidate_info"):
            self._provider._candidate_info = candidate_info

        logger.info(f"Local agent session started: {interview_type}")

        return {
            "status": "ok",
            "result": {
                "interview_type": interview_type,
                "candidate_info": candidate_info,
                "message": f"Local interview session started for {interview_type}",
            },
        }

    def get_question(self) -> str:
        """Get an interview question from underlying provider.

        Returns:
            Interview question tailored to candidate background
        """
        return self._provider.get_question()

    def get_phases(self) -> list[dict[str, str]]:
        """Get interview phases from underlying provider.

        Returns:
            List of phases with 'id' and 'name' keys
        """
        return self._provider.get_phases()

    def get_context(self, phase_id: str) -> str:
        """Get phase context from underlying provider.

        Args:
            phase_id: Phase identifier

        Returns:
            Context string for the phase
        """
        return self._provider.get_context(phase_id)

    def evaluate_phase(
        self, phase_id: str, conversation_history: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Evaluate phase completion using underlying provider.

        Args:
            phase_id: Phase identifier
            conversation_history: List of conversation messages

        Returns:
            Evaluation result with decision, score, and feedback
        """
        return self._provider.evaluate_phase(phase_id, conversation_history)
