"""Interview conductor tools - ADK LLM-based flow."""

import logging
import os
from typing import Any

from a2a.server.tasks import TaskUpdater
from a2a.types import DataPart, Part, Task, TaskState, TextPart
from google.adk.agents import LlmAgent
from google.genai import types as genai_types

from utils import find_data_part

logger = logging.getLogger(__name__)

# Interview agent
interview_agent = LlmAgent(
    name="google_interviewer",
    model=os.getenv("AGENT_MODEL", "gemini-2.0-flash-exp"),
    description="Google system design interviewer",
    instruction="""You are a senior Google engineer conducting a system design interview.

Focus areas:
- Scale: billions of users, QPS calculations, data volume
- Distributed systems: consistency, replication, sharding, CAP theorem
- Google tech: Spanner, Bigtable, MapReduce patterns
- Production: monitoring, reliability, disaster recovery

Interview flow:
1. Start with clarifying questions about requirements
2. Guide through high-level design
3. Deep dive into specific components
4. Discuss trade-offs and alternatives
5. End with questions and feedback

Be thorough but conversational. Ask probing questions.""",
)


async def conduct_interview(
    data_parts: list[dict],
    updater: TaskUpdater,
    current_task: Task | None,
) -> None:
    """Conduct system design interview using ADK LLM.

    Non-deterministic, conversational, multi-turn.
    """
    user_message = find_data_part("message", data_parts)
    user_id = find_data_part("user_id", data_parts) or updater.context_id
    session_id = find_data_part("session_id", data_parts) or updater.context_id

    if not user_message:
        await updater.failed(
            message=updater.new_agent_message(parts=[Part(root=TextPart(text="Missing message"))])
        )
        return

    logger.info(f"🎤 Interview turn for session {session_id[:8]}")

    try:
        # Run agent with message
        events = []
        async for event in interview_agent.run_async(
            user_id=user_id,
            session_id=session_id,
            new_message=genai_types.Content(
                role="user", parts=[genai_types.Part(text=user_message)]
            ),
        ):
            events.append(event)

        # Get final response
        if not events or not events[-1].message:
            raise ValueError("No response from interview agent")

        final_event = events[-1]
        response_text = _extract_text_from_content(final_event.message)

        logger.info(f"🎤 Interview response for {session_id[:8]}")

        # Always return message for multi-turn conversation
        await updater.add_artifact([Part(root=DataPart(data={"message": response_text}))])
        await updater.update_status(
            TaskState.input_required,
            updater.new_agent_message(parts=[Part(root=TextPart(text=response_text))]),
            final=True,
        )

    except Exception as e:
        logger.error(f"❌ Interview error: {e}", exc_info=True)
        await updater.failed(
            message=updater.new_agent_message(
                parts=[Part(root=TextPart(text=f"Interview error: {str(e)}"))]
            )
        )


def _extract_text_from_content(content: Any) -> str:
    """Extract text from GenAI Content object."""
    if not content or not hasattr(content, "parts"):
        return ""

    text_parts = []
    for part in content.parts:
        if hasattr(part, "text") and part.text:
            text_parts.append(part.text)

    return " ".join(text_parts)
