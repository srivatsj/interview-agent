"""
Phase Agent - Conducts a single interview phase with multi-turn conversation
Uses automatic evaluation to determine phase completion
"""

import logging
from typing import AsyncGenerator

from google.adk.agents import Agent, BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event, EventActions

from ...shared.constants import MODEL_NAME
from ...shared.prompts.prompt_loader import load_prompt

logger = logging.getLogger(__name__)


class PhaseAgent(BaseAgent):
    """Loop-based phase agent that conducts multi-turn conversation until phase complete"""

    # Pydantic configuration to allow arbitrary types and extra fields
    model_config = {"arbitrary_types_allowed": True, "extra": "allow"}

    def __init__(self, tool_provider):
        """
        Args:
            tool_provider: Company-specific tool provider (e.g., AmazonSystemDesignTools)
        """
        super().__init__(
            name="phase_agent",
            description="Conducts interview phase with automatic evaluation-based completion",
        )
        self.tool_provider = tool_provider

    def _get_phase_instruction(self, phase_id: str) -> str:
        """Generate phase-specific instruction.

        Args:
            phase_id: ID of the current phase

        Returns:
            Instruction string for the phase
        """
        phase_context = self.tool_provider.get_context(phase_id)

        # Load template and substitute phase-specific values
        template = load_prompt("phase_agent.txt")
        return (
            template.replace("{{phase_id}}", phase_id)
            .replace("{{phase_context}}", phase_context)
            .replace("{phase_id}", phase_id)
            .replace("{phase_context}", phase_context)
        )

    def _extract_conversation_history(self, ctx: InvocationContext) -> list[dict]:
        """Extract conversation history for evaluation.

        Args:
            ctx: Invocation context

        Returns:
            List of conversation messages
        """
        conversation = []
        for event in ctx.session.events:
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        conversation.append({"role": event.author, "content": part.text})
        return conversation

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """Loop until phase complete based on automatic evaluation.

        Flow:
        1. Get current phase from state
        2. Create LLM agent with phase context
        3. Loop:
           - Handle user message with LLM
           - Evaluate phase completion
           - If complete, exit loop
           - Otherwise, continue conversation
        """
        phase_id = ctx.session.state.get("current_phase", "unknown")
        logger.info(f"PhaseAgent starting loop for phase: {phase_id}")

        # Create instruction with phase context
        instruction = self._get_phase_instruction(phase_id)

        # Create inner LLM agent for this phase (no tools needed)
        llm_agent = Agent(
            model=MODEL_NAME,
            name=f"phase_{phase_id}_llm",
            description=f"Conducts {phase_id} phase conversation",
            tools=[],  # No tools - evaluation is automatic
            instruction=instruction,
        )

        # Track turns in this phase
        turn_count = 0

        # Loop until phase evaluation indicates completion
        while True:
            turn_count += 1
            logger.info(f"Phase {phase_id} - Turn {turn_count}")

            # Run LLM agent for this turn
            async for event in llm_agent.run_async(ctx):
                yield event

            # Extract conversation history for evaluation
            conversation_history = self._extract_conversation_history(ctx)

            # Evaluate phase completion
            evaluation = self.tool_provider.evaluate(phase_id, conversation_history)
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
                # Signal phase completion
                yield Event(
                    author=self.name,
                    actions=EventActions(state_delta={"phase_complete": True}),
                )
                break

            # Phase not complete - continue loop for next turn
            logger.info(
                f"Phase {phase_id} continuing. "
                f"Gaps: {evaluation.get('gaps', [])}. "
                f"Followup: {evaluation.get('followup_questions', '')}"
            )
