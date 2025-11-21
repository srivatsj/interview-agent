"""Run Google agent with custom A2A executor."""

import logging

import uvicorn
from a2a.server.apps import A2AStarletteApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCard, AgentSkill
from dotenv import load_dotenv

from agent_executor import GoogleAgentExecutor

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


# Agent card configuration
AGENT_CARD = AgentCard(
    name="google_system_design_agent",
    url="http://localhost:8001",
    description="Google system design interview expert with premium feedback",
    version="1.0.0",
    capabilities={},
    skills=[
        AgentSkill(
            id="create_cart_for_interview",
            name="Create Interview Cart",
            description="Creates cart mandate with pricing for Google interview purchase",
            tags=["payment", "cart", "interview"],
        ),
        AgentSkill(
            id="process_payment",
            name="Process Payment",
            description="Processes payment mandate via Credentials Provider",
            tags=["payment", "ap2", "stripe"],
        ),
        AgentSkill(
            id="conduct_interview",
            name="Conduct Interview",
            description="Conducts multi-turn system design interview with feedback",
            tags=["interview", "system_design", "google"],
        ),
    ],
    defaultInputModes=["text/plain"],
    defaultOutputModes=["application/json"],
    supportsAuthenticatedExtendedCard=False,
)


def create_server(host: str = "0.0.0.0", port: int = 8001):
    """Create A2A server with custom executor."""
    executor = GoogleAgentExecutor()

    request_handler = DefaultRequestHandler(
        agent_executor=executor,
        task_store=InMemoryTaskStore(),
    )

    app = A2AStarletteApplication(
        agent_card=AGENT_CARD,
        http_handler=request_handler,
    )

    return app.build()


# Create app at module level for uvicorn
app = create_server()

if __name__ == "__main__":
    logger.info("🚀 Starting Google System Design Agent on port 8001")
    logger.info("📋 Available skills: cart, payment, interview")
    uvicorn.run(app, host="0.0.0.0", port=8001)
