"""
Root Agent - Custom Interview Routing Agent

Uses BaseAgent with tool-based routing + deterministic delegation.
Reduces LLM calls by having explicit control flow.
"""

import logging
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

logger = logging.getLogger(__name__)


# Define the routing decision tool
def set_routing_decision(company: str, interview_type: str, tool_context: ToolContext) -> str:
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

    # Update state via ToolContext.state (ADK will automatically handle EventActions.state_delta)
    tool_context.state["routing_decision"] = routing_decision.model_dump()
    logger.info(f"Routing decision saved: {company.lower()} {interview_type.lower()}")

    return f"Routing saved: {company.lower()} {interview_type.lower()}"


# Create the routing agent at module level
routing_agent = Agent(
    model=MODEL_NAME,
    name="routing_conversation",
    description="Asks user for company and interview type preferences",
    tools=[set_routing_decision],
    instruction=load_prompt("routing_agent.txt"),
)


class RootCustomAgent(BaseAgent):
    """Custom agent with deterministic delegation after tool-based routing."""

    # Type hints for sub-agents (required by BaseAgent)
    routing_agent: Agent
    system_design_orchestrator: BaseAgent

    # Pydantic configuration to allow arbitrary types
    model_config = {"arbitrary_types_allowed": True}

    def __init__(
        self,
        routing_agent: Agent,
        system_design_orchestrator: BaseAgent,
    ):
        # Pass sub-agents to BaseAgent constructor
        super().__init__(
            name="interview_router",
            description="Routes users to appropriate interview with minimal LLM calls",
            routing_agent=routing_agent,
            system_design_orchestrator=system_design_orchestrator,
            sub_agents=[routing_agent, system_design_orchestrator],
        )

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        """
        Flow:
        1. Check if routing_decision exists in state
        2. If not, use LLM agent to collect routing via tool
        3. Once routing exists, deterministically delegate to sub-agent
        """
        routing_decision = ctx.session.state.get("routing_decision")

        # Step 1: If no routing, collect it first
        if not routing_decision:
            logger.info("No routing decision found, collecting from user...")
            async for event in self.routing_agent.run_async(ctx):
                yield event
            routing_decision = ctx.session.state.get("routing_decision")

        # Step 2: If routing exists (either was there or just collected), delegate to interview
        if routing_decision:
            interview_type = routing_decision.get("interview_type")
            logger.info(f"Delegating to {interview_type} interview")

            if interview_type == "system_design":
                async for event in self.system_design_orchestrator.run_async(ctx):
                    yield event
            elif interview_type == "coding":
                yield Event.create("Coding interviews coming soon. Try system_design!")
            elif interview_type == "behavioral":
                yield Event.create("Behavioral interviews coming soon. Try system_design!")
        else:
            logger.warning("No routing decision found after routing agent")


# Create the root agent instance with sub-agents
root_agent = RootCustomAgent(
    routing_agent=routing_agent,
    system_design_orchestrator=system_design_interview_orchestrator,
)
