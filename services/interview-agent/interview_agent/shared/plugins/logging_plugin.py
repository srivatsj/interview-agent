"""Logging plugin for ADK agents.

Logs important events during agent execution:
- Function calls (tools being executed)
- State changes (routing, candidate info, phases)
- Errors
"""

import logging

from google.adk.agents import BaseAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.plugins import BasePlugin

logger = logging.getLogger(__name__)


class LoggingPlugin(BasePlugin):
    """Logging plugin for integration tests.

    Logs important events:
    - Function calls with arguments
    - State changes (routing_decision, candidate_info, interview_phase)
    - LLM errors

    Usage:
        plugins = [LoggingPlugin()]
        runner = Runner(..., plugins=plugins)
    """

    def __init__(self):
        super().__init__(name="logging")

    async def before_agent_callback(
        self, *, agent: BaseAgent, callback_context: CallbackContext
    ) -> None:
        """Log when an agent starts execution."""
        # Just log agent name
        logger.info(f"[AGENT] {agent.name} starting")

    async def after_agent_callback(
        self, *, agent: BaseAgent, callback_context: CallbackContext
    ) -> None:
        """Log state changes after agent execution."""
        if not callback_context.session or not callback_context.session.state:
            return

        state = callback_context.session.state

        # Log important state changes
        if "routing_decision" in state:
            routing = state["routing_decision"]
            logger.info(f"[STATE] routing_decision: {routing}")

        if "candidate_info" in state:
            candidate = state["candidate_info"]
            logger.info(f"[STATE] candidate_info: {candidate}")

        if "interview_phase" in state:
            phase = state["interview_phase"]
            logger.info(f"[STATE] interview_phase: {phase}")

    async def before_model_callback(
        self, *, callback_context: CallbackContext, llm_request: LlmRequest
    ) -> None:
        """Log before sending request to LLM."""
        # Don't log anything before model - too noisy
        pass

    async def after_model_callback(
        self, *, callback_context: CallbackContext, llm_response: LlmResponse
    ) -> None:
        """Log function calls and errors from LLM."""
        # Log errors
        if llm_response.error_message:
            logger.error(f"[ERROR] {callback_context.agent_name}: {llm_response.error_message}")
            return

        # Log function calls (important!)
        if llm_response.content and llm_response.content.parts:
            for part in llm_response.content.parts:
                if part.function_call:
                    logger.info(f"[TOOL_CALL] {part.function_call.name}")
                    logger.info(f"[TOOL_ARGS] {part.function_call.args}")
