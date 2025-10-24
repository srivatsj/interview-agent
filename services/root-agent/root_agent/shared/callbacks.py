"""Logging callbacks for debugging agent flow"""

import logging
from typing import Optional

from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

logger = logging.getLogger(__name__)


# ============================================================================
# Agent Lifecycle Callbacks
# ============================================================================


def log_before_agent(callback_context: CallbackContext) -> Optional[types.Content]:
    """Log when an agent starts execution."""
    agent_name = callback_context.agent_name
    invocation_id = callback_context.invocation_id

    logger.info("=" * 80)
    logger.info(f"[BEFORE_AGENT] Agent '{agent_name}' starting")
    logger.info(f"[BEFORE_AGENT] Invocation ID: {invocation_id}")

    # Log current session state
    state = callback_context.state.to_dict()
    if state:
        logger.info(f"[BEFORE_AGENT] Session state keys: {list(state.keys())}")
        # Log specific important state
        if "routing_decision" in state:
            logger.info(f"[BEFORE_AGENT] Routing decision: {state['routing_decision']}")
        if "interview_phase" in state:
            logger.info(f"[BEFORE_AGENT] Interview phase: {state['interview_phase']}")
        if "candidate_info" in state:
            logger.info("[BEFORE_AGENT] Candidate info present: Yes")
    else:
        logger.info("[BEFORE_AGENT] Session state: empty")

    logger.info("=" * 80)

    return None  # Allow agent to execute normally


def log_after_agent(callback_context: CallbackContext) -> Optional[types.Content]:
    """Log when an agent completes execution."""
    agent_name = callback_context.agent_name
    invocation_id = callback_context.invocation_id

    logger.info("=" * 80)
    logger.info(f"[AFTER_AGENT] Agent '{agent_name}' completed")
    logger.info(f"[AFTER_AGENT] Invocation ID: {invocation_id}")

    # Log updated session state
    state = callback_context.state.to_dict()
    if state:
        logger.info(f"[AFTER_AGENT] Session state keys: {list(state.keys())}")
        # Log specific important state
        if "routing_decision" in state:
            logger.info(f"[AFTER_AGENT] Routing decision: {state['routing_decision']}")
        if "interview_phase" in state:
            logger.info(f"[AFTER_AGENT] Interview phase: {state['interview_phase']}")
        if "candidate_info" in state:
            logger.info("[AFTER_AGENT] Candidate info present: Yes")

    logger.info("=" * 80)

    return None  # Use agent's original output


# ============================================================================
# Model Callbacks
# ============================================================================


def log_before_model(
    callback_context: CallbackContext, llm_request: LlmRequest
) -> Optional[LlmResponse]:
    """Log before sending request to LLM."""
    agent_name = callback_context.agent_name
    logger.info(f"[BEFORE_MODEL] Agent: {agent_name}")

    # Log user message if present
    if llm_request.contents and len(llm_request.contents) > 0:
        last_content = llm_request.contents[-1]
        if last_content.role == "user" and last_content.parts:
            user_msg = last_content.parts[0].text if last_content.parts[0].text else ""
            logger.info(f"[BEFORE_MODEL] User message: {user_msg[:200]}...")

    # Log system instruction
    if llm_request.config and llm_request.config.system_instruction:
        instruction = llm_request.config.system_instruction
        if isinstance(instruction, str):
            logger.info(f"[BEFORE_MODEL] System instruction: {instruction[:200]}...")
        elif instruction and hasattr(instruction, "parts") and instruction.parts:
            sys_text = instruction.parts[0].text if instruction.parts[0].text else ""
            logger.info(f"[BEFORE_MODEL] System instruction: {sys_text[:200]}...")

    return None  # Allow normal execution


def log_after_model(
    callback_context: CallbackContext, llm_response: LlmResponse
) -> Optional[LlmResponse]:
    """Log after receiving response from LLM."""
    agent_name = callback_context.agent_name
    logger.info(f"[AFTER_MODEL] Agent: {agent_name}")

    # Log response content
    if llm_response.content and llm_response.content.parts:
        for part in llm_response.content.parts:
            if part.text:
                logger.info(f"[AFTER_MODEL] Response: {part.text[:200]}...")
            if part.function_call:
                logger.info(f"[AFTER_MODEL] Function call: {part.function_call.name}")
                logger.info(f"[AFTER_MODEL] Function args: {part.function_call.args}")

    # Log any errors
    if llm_response.error_message:
        logger.error(f"[AFTER_MODEL] Error: {llm_response.error_message}")

    return None  # Use original response
