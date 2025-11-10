"""Root Agent - Single LlmAgent with State-Driven Instruction.

Uses Live API for persistent bidirectional audio/video streaming.
Adapts behavior based on interview_phase state.
"""

import logging

from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.agents.readonly_context import ReadonlyContext

from .interview_types.system_design.design_agent_tool import (
    initialize_design_phase,
    mark_design_complete,
)
from .shared.agent_providers import AgentProviderRegistry
from .shared.constants import MODEL_WITH_AUDIO
from .shared.prompts.prompt_loader import load_prompt
from .shared.tools.closing_tools import mark_interview_complete
from .shared.tools.intro_tools import save_candidate_info
from .shared.tools.routing_tools import set_routing_decision

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


def get_dynamic_instruction(ctx: ReadonlyContext) -> str:
    """Generate instruction based on current interview phase.

    Instruction adapts to: routing → intro → design → closing → done
    State changes via tools trigger automatic instruction updates.

    Args:
        ctx: Readonly context with session state

    Returns:
        Phase-specific instruction string
    """
    phase = ctx.session.state.get("interview_phase", "routing")
    routing = ctx.session.state.get("routing_decision", {})
    candidate_info = ctx.session.state.get("candidate_info", {})

    company = routing.get("company", "COMPANY")
    interview_type = routing.get("interview_type", "INTERVIEW_TYPE")
    candidate_name = candidate_info.get("name", "CANDIDATE")

    if phase == "routing":
        # Ask user for company and interview type preferences
        available_options = AgentProviderRegistry.get_formatted_options()
        return load_prompt("routing_agent.txt", available_options=available_options)

    elif phase == "intro":
        # Collect candidate background information
        return load_prompt(
            "intro_agent.txt",
            company=company,
            interview_type=interview_type,
        )

    elif phase == "design":
        # Conduct system design interview
        interview_question = ctx.session.state.get("interview_question", "")
        if not interview_question:
            # Question not yet loaded - prompt to initialize
            return (
                "The design phase is ready to begin. "
                "Use the initialize_design_phase tool to load the interview question."
            )
        else:
            # Question loaded - conduct interview
            return load_prompt(
                "design_phase.txt",
                company=company,
                interview_type=interview_type,
                candidate_name=candidate_name,
                interview_question=interview_question,
            )

    elif phase == "closing":
        # Wrap up and thank candidate
        return load_prompt(
            "closing_agent.txt",
            company=company,
            interview_type=interview_type,
            candidate_name=candidate_name,
        )

    else:  # phase == "done"
        # Interview complete
        return "Interview is complete. Thank the candidate and end the session."


# Root agent - Single LlmAgent with Live API for persistent connection
root_agent = Agent(
    name="interview_agent",
    model=MODEL_WITH_AUDIO,
    description="Conducts technical interviews with multi-phase flow",
    instruction=get_dynamic_instruction,  # Dynamic instruction based on phase
    tools=[
        # Routing phase tools
        set_routing_decision,
        # Intro phase tools
        save_candidate_info,
        # Design phase tools
        initialize_design_phase,
        mark_design_complete,
        # Closing phase tools
        mark_interview_complete,
    ],
)
