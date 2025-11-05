"""Phase completion checker agent"""

import logging
from typing import AsyncGenerator

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions

logger = logging.getLogger(__name__)


class PhaseCompletionChecker(BaseAgent):
    """Evaluates phase completion and signals loop exit via escalation."""

    model_config = {"arbitrary_types_allowed": True, "extra": "allow"}

    def __init__(self, tool_provider):
        """
        Args:
            tool_provider: Company-specific tool provider for evaluation
        """
        super().__init__(
            name="phase_completion_checker",
            description="Evaluates phase completion and signals when to exit loop",
        )
        self.tool_provider = tool_provider

    def _extract_conversation_history(self, ctx: InvocationContext) -> list[dict]:
        """Extract conversation history for evaluation.

        Args:
            ctx: Invocation context

        Returns:
            List of conversation messages with role and content
        """
        conversation = []
        for event in ctx.session.events:
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        conversation.append({"role": event.author, "content": part.text})
        return conversation

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Evaluate phase completion and escalate if done.

        Checks conversation history against phase completion criteria.
        Sets escalate=True when phase is complete to exit the loop.
        """
        phase_id = ctx.session.state.get("current_phase", "unknown")

        # Track turn count
        turn_count = ctx.session.state.get("phase_turn_count", 0)
        turn_count += 1
        ctx.session.state["phase_turn_count"] = turn_count

        logger.info(f"Phase {phase_id} - Evaluating turn {turn_count}")

        # Extract conversation history
        conversation_history = self._extract_conversation_history(ctx)

        # Evaluate phase completion
        evaluation = await self.tool_provider.evaluate_phase(phase_id, conversation_history)
        logger.info(
            f"Phase {phase_id} evaluation: {evaluation.get('decision')} "
            f"(score: {evaluation.get('score', 0)})"
        )

        # Check if phase is complete
        if evaluation.get("decision") == "next_phase":
            logger.info(
                f"Phase {phase_id} complete after {turn_count} turns. "
                f"Message: {evaluation.get('message')}"
            )
            # Signal completion via escalation
            yield Event(
                author=self.name,
                actions=EventActions(escalate=True, state_delta={"phase_complete": True}),
            )
        else:
            # Phase not complete - loop continues
            logger.info(
                f"Phase {phase_id} continuing. "
                f"Gaps: {evaluation.get('gaps', [])}. "
                f"Followup: {evaluation.get('followup_questions', '')}"
            )
            yield Event(author=self.name)
