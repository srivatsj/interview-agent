"""
Root Agent - Custom Interview Routing Agent

Uses BaseAgent with tool-based routing + deterministic delegation.
Reduces LLM calls by having explicit control flow.
"""

from typing import AsyncGenerator

from dotenv import load_dotenv
from google.adk.agents import Agent, BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.adk.tools import ToolContext

from .interview_types.system_design.main_agent import system_design_interview_orchestrator
from .shared.constants import MODEL_NAME, SUPPORTED_COMPANIES, SUPPORTED_INTERVIEW_TYPES
from .shared.prompts.prompt_loader import load_prompt
from .shared.schemas import RoutingDecision

# Load environment variables
load_dotenv()


class RootCustomAgent(BaseAgent):
    """Custom agent with deterministic delegation after tool-based routing."""

    def __init__(self):
        super().__init__(
            name="interview_router",
            description="Routes users to appropriate interview with minimal LLM calls",
        )
        # Initialize sub-agents inside the class
        self._init_routing_agent()
        self._init_orchestrators()

    def _init_routing_agent(self):
        """Initialize the routing LLM agent with tool"""
        self._routing_agent = Agent(
            model=MODEL_NAME,
            name="routing_conversation",
            description="Asks user for company and interview type preferences",
            tools=[self._set_routing_decision],
            instruction=load_prompt("routing_agent.txt"),
        )

    def _init_orchestrators(self):
        """Initialize interview orchestrators"""
        self._system_design_orchestrator = system_design_interview_orchestrator

    @staticmethod
    def _set_routing_decision(tool_context: ToolContext, company: str, interview_type: str) -> str:
        """Save the routing decision to session state.

        Use this when you've determined which company and interview type the user wants.

        Args:
            company: The company (amazon, google, or apple)
            interview_type: The interview type (system_design, coding, or behavioral)

        Returns:
            Confirmation message
        """
        # Validate company
        if company.lower() not in SUPPORTED_COMPANIES:
            companies = ", ".join(SUPPORTED_COMPANIES)
            return f"Error: Invalid company '{company}'. Must be one of: {companies}"

        # Validate interview type
        if interview_type.lower() not in SUPPORTED_INTERVIEW_TYPES:
            types = ", ".join(SUPPORTED_INTERVIEW_TYPES)
            return f"Error: Invalid interview type '{interview_type}'. Must be one of: {types}"

        routing_decision = RoutingDecision(
            company=company.lower(), interview_type=interview_type.lower(), confidence=1.0
        )

        tool_context.session.state["routing_decision"] = routing_decision.model_dump()

        return f"Routing saved: {company.lower()} {interview_type.lower()}"

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """
        Flow:
        1. Check if routing_decision exists in state
        2. If not, use LLM agent to collect routing via tool
        3. Once routing exists, deterministically delegate to sub-agent
        """
        routing_decision = ctx.session.state.get("routing_decision")

        if routing_decision:
            # Routing exists - deterministically delegate
            interview_type = routing_decision.get("interview_type")

            if interview_type == "system_design":
                async for event in self._system_design_orchestrator._run_async_impl(ctx):
                    yield event
            elif interview_type == "coding":
                yield Event.create("Coding interviews coming soon. Try system_design!")
            elif interview_type == "behavioral":
                yield Event.create("Behavioral interviews coming soon. Try system_design!")
        else:
            # No routing - use LLM to collect it via tool
            async for event in self._routing_agent._run_async_impl(ctx):
                yield event


# Create the root agent instance
root_agent = RootCustomAgent()
