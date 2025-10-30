"""Client for communicating with remote interview agents via A2A protocol."""

import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class RemoteAgentProvider:
    """Client for calling remote interview agent skills via A2A protocol."""

    def __init__(self, agent_url: str, timeout: float = 30.0):
        """Initialize remote agent provider.

        Args:
            agent_url: Base URL of the remote agent
            timeout: Request timeout in seconds
        """
        self.agent_url = agent_url.rstrip("/")
        self.timeout = timeout
        self._session_id: str | None = None
        self._candidate_info: dict[str, Any] = {}

    async def start_interview(
        self, interview_type: str, candidate_info: dict[str, Any]
    ) -> dict[str, Any]:
        """Start an interview session with the remote agent.

        Args:
            interview_type: Type of interview (e.g., 'system_design')
            candidate_info: Candidate background information

        Returns:
            Response from remote agent

        Raises:
            httpx.HTTPError: If request fails
        """
        payload = {
            "skill": "start_interview",
            "args": {
                "interview_type": interview_type,
                "candidate_info": candidate_info,
            },
        }

        result = await self._call_skill(payload)
        self._candidate_info = candidate_info
        return result

    async def get_question(self) -> str:
        """Get an interview question tailored to candidate background.

        Returns:
            Interview question
        """
        result = await self._call_skill({"skill": "get_question"})
        return result.get("result", {}).get("question", "")

    async def get_phases(self) -> list[dict[str, str]]:
        """Get interview phases from remote agent.

        Returns:
            List of phases with id and name
        """
        result = await self._call_skill({"skill": "get_phases"})
        return result.get("result", {}).get("phases", [])

    async def get_context(self, phase_id: str) -> str:
        """Get guidance for a specific phase.

        Args:
            phase_id: Phase identifier

        Returns:
            Context string for the phase
        """
        result = await self._call_skill({"skill": "get_context", "args": {"phase_id": phase_id}})
        return result.get("result", {}).get("context", "")

    async def evaluate_phase(
        self, phase_id: str, conversation_history: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Evaluate phase completion based on conversation history.

        Args:
            phase_id: Phase identifier
            conversation_history: List of conversation messages

        Returns:
            Evaluation result with decision, score, and feedback
        """
        payload = {
            "skill": "evaluate_phase",
            "args": {
                "phase_id": phase_id,
                "conversation_history": conversation_history,
            },
        }

        result = await self._call_skill(payload)
        return result.get("result", {}).get("evaluation", {})

    async def _call_skill(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Call a remote agent skill via A2A protocol.

        Args:
            payload: Skill payload

        Returns:
            Response from remote agent

        Raises:
            httpx.HTTPError: If request fails
            ValueError: If response indicates error
        """
        url = f"{self.agent_url}/a2a/invoke"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            logger.debug(f"Calling {url} with payload: {payload}")

            response = await client.post(
                url,
                json={"content": json.dumps(payload)},
                headers={"Content-Type": "application/json"},
            )

            response.raise_for_status()
            data = response.json()

            # Extract message from A2A response
            message_text = data.get("content", "{}")
            result = json.loads(message_text)

            # Check for errors
            if result.get("status") == "error":
                error = result.get("error", {})
                error_code = error.get("code")
                error_msg = error.get("message")
                raise ValueError(f"Remote agent error: {error_code} - {error_msg}")

            logger.debug(f"Remote agent response: {result}")
            return result
