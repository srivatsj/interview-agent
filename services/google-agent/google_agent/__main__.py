"""CLI entrypoint for the Google system design remote agent."""

from __future__ import annotations

import logging

import click
import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, AgentSkill

from .executor import GoogleAgentExecutor

logging.basicConfig(level=logging.INFO)


def build_agent_card(host: str, port: int) -> AgentCard:
    """Construct the agent card advertised to remote orchestrators."""
    return AgentCard(
        name="Google System Design Agent",
        description="Remote agent that plans and conducts Google-style system design interviews.",
        url=f"http://{host}:{port}/",
        version="0.1.0",
        default_input_modes=["text"],
        default_output_modes=["text"],
        capabilities=AgentCapabilities(streaming=False),
        skills=[
            AgentSkill(
                id="get_phases",
                name="List Interview Phases",
                description="Return the ordered list of system design interview phases.",
                tags=["system-design", "google", "phases"],
                examples=['{"skill": "get_phases"}'],
            ),
            AgentSkill(
                id="get_context",
                name="Describe Phase Expectations",
                description="Provide guidance for a specific phase by its identifier.",
                tags=["system-design", "context"],
                examples=[
                    '{"skill": "get_context", "args": {"phase_id": "plan_and_scope"}}',
                ],
            ),
            AgentSkill(
                id="evaluate_phase",
                name="Evaluate Phase Coverage",
                description="Score the conversation history for a phase and suggest follow-ups.",
                tags=["evaluation", "feedback"],
                examples=[
                    (
                        '{"skill": "evaluate_phase", "args": {"phase_id": "plan_and_scope", '
                        '"conversation_history": [{"role": "user", "content": "..."}]}}'
                    ),
                ],
            ),
        ],
    )


@click.command()
@click.option("--host", "host", default="0.0.0.0")
@click.option("--port", "port", default=10123)
def main(host: str, port: int) -> None:
    """Start the Google system design remote agent server."""
    agent_card = build_agent_card(host, port)
    executor = GoogleAgentExecutor()
    request_handler = DefaultRequestHandler(agent_executor=executor, task_store=InMemoryTaskStore())

    app = A2AStarletteApplication(agent_card=agent_card, http_handler=request_handler)
    uvicorn.run(app.build(), host=host, port=port)


if __name__ == "__main__":
    main()
