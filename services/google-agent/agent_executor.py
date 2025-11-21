"""Custom A2A executor for Google agent - Routes to deterministic or LLM-based tools."""

import logging

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import InvalidParamsError, Part, TextPart
from a2a.utils.errors import ServerError

from tools.interview_tools import conduct_interview
from tools.payment_tools import create_cart_for_interview, process_payment
from utils import parse_request_parts

logger = logging.getLogger(__name__)


class GoogleAgentExecutor(AgentExecutor):
    """Custom executor with deterministic routing.

    Routes requests to appropriate tools based on text command:
    - Payment tools: Deterministic A2A flow
    - Interview tools: ADK LLM-based flow
    """

    def __init__(self):
        super().__init__()
        self.tool_registry = {
            "create_cart": create_cart_for_interview,
            "cart": create_cart_for_interview,
            "process_payment": process_payment,
            "payment": process_payment,
            "interview": conduct_interview,
            "design": conduct_interview,
        }

    async def execute(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Execute agent logic with deterministic tool routing."""
        if not context.message:
            raise ServerError(error=InvalidParamsError("Missing message"))

        # Parse message into text and data parts
        text_parts, data_parts = parse_request_parts(context.message)

        if not text_parts:
            raise ServerError(error=InvalidParamsError("Missing text command"))

        # Route to appropriate tool
        command = text_parts[0].lower()
        tool_func = self._find_tool(command)

        if not tool_func:
            await self._fail_task(
                event_queue,
                context,
                f"Unknown command: {command}. Available: cart, payment, interview",
            )
            return

        # Execute tool
        logger.info(f"📍 Routing '{command}' to {tool_func.__name__}")
        updater = TaskUpdater(
            event_queue,
            task_id=context.task_id,
            context_id=context.context_id,
        )

        try:
            await tool_func(data_parts, updater, context.current_task)
        except Exception as e:
            logger.error(f"❌ Tool execution failed: {e}", exc_info=True)
            await self._fail_task(event_queue, context, str(e))

    async def cancel(self, context: RequestContext, event_queue: EventQueue) -> None:
        """Cancel execution (not implemented)."""
        pass

    def _find_tool(self, command: str):
        """Find tool function for command.

        Simple keyword matching - no nested loops.
        """
        for keyword, tool_func in self.tool_registry.items():
            if keyword in command:
                return tool_func
        return None

    async def _fail_task(
        self,
        event_queue: EventQueue,
        context: RequestContext,
        error_msg: str,
    ) -> None:
        """Helper to fail task with error message."""
        updater = TaskUpdater(
            event_queue,
            task_id=context.task_id,
            context_id=context.context_id,
        )
        message = updater.new_agent_message(parts=[Part(root=TextPart(text=error_msg))])
        await updater.failed(message=message)
        logger.error(f"Task failed: {error_msg}")
