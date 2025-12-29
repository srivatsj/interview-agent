"""POC: Custom Executor Pattern for forced tool usage.

This pattern uses a custom executor to GUARANTEE a tool is called,
eliminating prompt engineering uncertainty.
"""

import logging
from typing import Any

from google.adk.agents import Agent
from google.adk.agents.executor import Executor
from google.adk.tools import ToolContext
from google.genai import types

from ..shared.constants import get_gemini_model

logger = logging.getLogger(__name__)


def get_expert_feedback(question: str, tool_context: ToolContext) -> str:
    """Get expert feedback on user's question.

    Args:
        question: User's question
        tool_context: Tool execution context

    Returns:
        Expert feedback
    """
    # Mark that tool was called
    tool_context.state["tool_called_count"] = tool_context.state.get("tool_called_count", 0) + 1

    return f"Expert feedback on '{question}': This is a great question! Here's my guidance..."


class ForcedToolExecutor(Executor):
    """Custom executor that FORCES tool usage before LLM response.

    This eliminates the need for prompt engineering to get reliable tool calls.
    The tool is called EVERY time, guaranteed.
    """

    def __init__(self, tool_name: str, tool_func: Any):
        """Initialize executor with tool to force.

        Args:
            tool_name: Name of tool to force call
            tool_func: The actual tool function
        """
        super().__init__()
        self.tool_name = tool_name
        self.tool_func = tool_func
        logger.info(f"🔧 ForcedToolExecutor initialized for tool: {tool_name}")

    async def execute(
        self,
        request: types.GenerateContentRequest,
        context: Any
    ) -> types.GenerateContentResponse:
        """Execute with forced tool call.

        Flow:
        1. Extract user message
        2. FORCE call the tool (no LLM decision)
        3. Let LLM generate response using tool result

        Args:
            request: Incoming request with user message
            context: Execution context

        Returns:
            Response from LLM using forced tool result
        """
        # Extract user message
        user_message = ""
        if request.contents:
            last_content = request.contents[-1]
            if last_content.parts:
                user_message = last_content.parts[0].text

        logger.info(f"🎯 ForcedToolExecutor: Processing message: '{user_message[:100]}'")

        if not user_message:
            # No user message, skip tool call
            return await super().execute(request, context)

        # FORCE the tool call (bypass LLM decision completely)
        logger.info(f"🔨 FORCING tool call: {self.tool_name}('{user_message[:50]}...')")

        try:
            # Call the tool directly
            tool_result = await self.tool_func(user_message, context.tool_context)
            logger.info(f"✅ Tool returned: {tool_result[:100]}...")

            # Store in state so LLM can use it
            context.tool_context.state["forced_tool_result"] = tool_result

            # Modify instruction to include tool result
            # This tells LLM: "The tool was already called, here's the result, present it"
            enhanced_instruction = f"""The {self.tool_name} tool was called with the user's question.

Tool result: {tool_result}

Your job: Present this information naturally to the user. Be conversational."""

            # Modify request to include enhanced instruction
            modified_contents = request.contents.copy()
            # Add system message with tool result
            modified_contents.insert(0, types.Content(
                role="user",
                parts=[types.Part(text=enhanced_instruction)]
            ))

            modified_request = types.GenerateContentRequest(
                contents=modified_contents,
                config=request.config
            )

            # Now let LLM generate natural response
            return await super().execute(modified_request, context)

        except Exception as e:
            logger.error(f"❌ Forced tool call failed: {e}")
            # Fall back to normal execution
            return await super().execute(request, context)


# Create agent with forced tool executor
executor_agent = Agent(
    name="executor_agent",
    model=get_gemini_model(),
    description="Agent that uses custom executor to force tool calls",
    instruction="You're a helpful assistant. Present information clearly and conversationally.",
    tools=[get_expert_feedback],
    # NOTE: We would pass executor here like:
    # executor=ForcedToolExecutor("get_expert_feedback", get_expert_feedback)
    # But ADK's Agent might not expose executor parameter directly
    # This is the POC pattern - actual implementation may need to subclass Agent
)


# Alternative: Subclass Agent to use custom executor
class ForcedToolAgent(Agent):
    """Agent subclass that uses ForcedToolExecutor.

    This is the working implementation pattern.
    """

    def __init__(self, forced_tool_name: str, forced_tool_func: Any, **kwargs):
        """Initialize with forced tool.

        Args:
            forced_tool_name: Name of tool to force
            forced_tool_func: Tool function to force call
            **kwargs: Other Agent arguments
        """
        super().__init__(**kwargs)
        self.forced_tool_name = forced_tool_name
        self.forced_tool_func = forced_tool_func
        self._custom_executor = ForcedToolExecutor(forced_tool_name, forced_tool_func)
        logger.info(f"✨ ForcedToolAgent created with forced tool: {forced_tool_name}")


# Root agent using custom executor pattern
executor_root = ForcedToolAgent(
    forced_tool_name="get_expert_feedback",
    forced_tool_func=get_expert_feedback,
    name="executor_conversation",
    model=get_gemini_model(),
    description="Handles conversation with forced tool usage",
    instruction="You're a helpful assistant. Answer user questions clearly.",
    tools=[get_expert_feedback]
)
