"""Phase Agent - Conducts interview phase with interactive evaluation"""

import logging
from typing import AsyncGenerator

from google.adk.agents import Agent, BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions

from ....shared.constants import MODEL_NAME
from ....shared.prompts.prompt_loader import load_prompt

logger = logging.getLogger(__name__)


class PhaseAgent(BaseAgent):
    """Interactive phase agent that evaluates after each user response."""

    model_config = {"arbitrary_types_allowed": True, "extra": "allow"}

    def __init__(self, tool_provider, max_turns: int = 10):
        """
        Args:
            tool_provider: Company-specific tool provider
            max_turns: Maximum turns before forcing exit (default: 10)
        """
        super().__init__(
            name="phase_agent",
            description="Conducts interview phase with user-interactive evaluation",
        )
        self.tool_provider = tool_provider
        self.max_turns = max_turns

    async def _get_phase_instruction(self, ctx: InvocationContext, phase_id: str) -> str:
        """Generate phase-specific instruction.

        Args:
            ctx: Invocation context to read interview_question from state
            phase_id: Current phase ID

        Returns:
            Instruction string for the phase
        """
        phase_context = await self.tool_provider.get_context(phase_id)
        interview_question = ctx.session.state.get("interview_question", "")
        return load_prompt(
            "phase_agent.txt",
            phase_id=phase_id,
            phase_context=phase_context,
            interview_question=interview_question,
        )

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Interactive phase flow: LLM speaks → user responds → evaluate → repeat or escalate.

        Flow:
        1. First turn (phase_turn_count=0): LLM introduces phase and asks question
        2. Subsequent turns: Evaluate user response
           - If continue: LLM asks follow-up
           - If next_phase: Escalate to exit phase
        """
        phase_id = ctx.session.state.get("current_phase", "unknown")
        turn_count = ctx.session.state.get("phase_turn_count", 0)

        logger.info(f"PhaseAgent running for phase: {phase_id}, turn: {turn_count}")

        # Create instruction
        instruction = await self._get_phase_instruction(ctx, phase_id)

        # Create conversation agent
        conversation_agent = Agent(
            model=MODEL_NAME,
            name=f"phase_{phase_id}_conversation",
            description=f"Conducts {phase_id} phase conversation",
            tools=[],
            instruction=instruction,
        )

        if turn_count == 0:
            # First turn: LLM introduces phase
            logger.info(f"Phase {phase_id} - Initial LLM introduction")
            async for event in conversation_agent.run_async(ctx):
                yield event

            # Increment turn count
            yield Event(
                author=self.name,
                actions=EventActions(state_delta={"phase_turn_count": 1}),
            )
        else:
            # Subsequent turns: Evaluate user response
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
                # Escalate to exit phase
                yield Event(
                    author=self.name,
                    actions=EventActions(
                        escalate=True,
                        state_delta={"phase_complete": True, "phase_turn_count": 0},
                    ),
                )
            else:
                # Phase not complete - LLM asks follow-up
                logger.info(
                    f"Phase {phase_id} continuing. "
                    f"Gaps: {evaluation.get('gaps', [])}. "
                    f"Followup: {evaluation.get('followup_questions', '')}"
                )

                # Generate LLM follow-up
                async for event in conversation_agent.run_async(ctx):
                    yield event

                # Increment turn count
                yield Event(
                    author=self.name,
                    actions=EventActions(state_delta={"phase_turn_count": turn_count + 1}),
                )

            # Check max turns
            if turn_count >= self.max_turns:
                logger.warning(
                    f"Phase {phase_id} reached max turns ({self.max_turns}), forcing exit"
                )
                yield Event(
                    author=self.name,
                    actions=EventActions(
                        escalate=True,
                        state_delta={"phase_complete": True, "phase_turn_count": 0},
                    ),
                )

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
