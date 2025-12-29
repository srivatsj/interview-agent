"""POC: Custom Agent Pattern for forced tool usage.

CORRECTED IMPLEMENTATION based on ADK documentation.

Instead of a custom executor, ADK uses Custom Agents that inherit from BaseAgent
and override _run_async_impl to control execution flow.
"""

import logging
from typing import AsyncGenerator

from google.adk.agents import BaseAgent, Agent
from google.adk.runtime import InvocationContext, Event
from google.adk.tools import ToolContext

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


class ForcedToolAgent(BaseAgent):
    """Custom Agent that FORCES tool usage before every response.

    This is the CORRECT way to customize agent behavior in ADK.
    Instead of an "executor", we override _run_async_impl to control flow.
    """

    def __init__(
        self,
        expert_tool_func,
        response_agent: Agent,
        **kwargs
    ):
        """Initialize custom agent.

        Args:
            expert_tool_func: The tool function to force call
            response_agent: LLM agent that formats the response
            **kwargs: BaseAgent arguments (name, description, etc.)
        """
        # Initialize BaseAgent with response_agent as sub-agent
        super().__init__(
            sub_agents=[response_agent],
            **kwargs
        )
        self.expert_tool = expert_tool_func
        self.response_agent = response_agent
        logger.info(f"✨ ForcedToolAgent created: {kwargs.get('name')}")

    async def _run_async_impl(
        self,
        ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        """Custom execution logic that FORCES tool call.

        Flow:
        1. Extract user message
        2. FORCE call expert tool (no LLM decision)
        3. Store result in state
        4. Let response agent format the answer

        Args:
            ctx: Invocation context with session state

        Yields:
            Events from the response agent
        """
        logger.info(f"🎯 ForcedToolAgent: Starting execution")

        # Get user's message from the request
        # The last user message is what we need to process
        user_message = ctx.input_text or ""

        if not user_message:
            logger.warning("⚠️ No user message found, skipping tool call")
            # Just run response agent without tool call
            async for event in self.response_agent.run_async(ctx):
                yield event
            return

        logger.info(f"📝 User message: {user_message[:100]}...")

        # FORCE the tool call (bypass LLM decision completely)
        logger.info(f"🔨 FORCING tool call: get_expert_feedback")

        try:
            # Create a ToolContext from the session state
            from google.adk.tools import ToolContext
            tool_ctx = ToolContext(
                state=ctx.session.state,
                invocation_id=ctx.invocation_id,
                session=ctx.session
            )

            # Call the tool directly
            tool_result = self.expert_tool(user_message, tool_ctx)
            logger.info(f"✅ Tool returned: {tool_result[:100]}...")

            # Store in state for response agent to use
            ctx.session.state["expert_tool_result"] = tool_result
            ctx.session.state["forced_tool_called"] = True

        except Exception as e:
            logger.error(f"❌ Forced tool call failed: {e}")
            ctx.session.state["expert_tool_result"] = f"Error: {str(e)}"
            ctx.session.state["forced_tool_called"] = False

        # Now run the response agent which will use the tool result
        logger.info("🤖 Running response agent to format answer")
        async for event in self.response_agent.run_async(ctx):
            yield event

        logger.info("✅ ForcedToolAgent: Execution complete")


# Create response formatter agent (LLM that presents the tool result)
response_formatter = Agent(
    name="response_formatter",
    model=get_gemini_model(),
    description="Formats expert feedback into conversational response",
    instruction="""You're a helpful assistant presenting expert feedback.

The expert tool has been called and returned this result:
{expert_tool_result}

Your job: Present this information naturally and conversationally to the user.
Be friendly and helpful."""
)


# Create the custom forced tool agent
custom_root = ForcedToolAgent(
    expert_tool_func=get_expert_feedback,
    response_agent=response_formatter,
    name="forced_tool_conversation",
    description="Handles conversation with guaranteed tool usage via custom agent"
)
