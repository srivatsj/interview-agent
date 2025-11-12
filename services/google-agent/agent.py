"""
Google System Design Interview Agent - Exposed via A2A Protocol

This agent has 2 skills:
1. Analyze Scale Requirements - Calculate scale for billions of users
2. Design Distributed Systems - Suggest distributed architecture patterns
"""
import os

from a2a.types import AgentCard, AgentSkill
from dotenv import load_dotenv
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.agents import Agent

# Load environment variables from .env file
load_dotenv()


# Skill 1: Analyze Scale Requirements
def analyze_scale_requirements(scenario: str) -> dict:
    """
    Analyze scale requirements for massive-scale systems.

    This is SKILL 1: Analyze Scale Requirements
    Use for: billion-user scenarios, global scale calculations, data center planning

    Args:
        scenario: Description of the scenario (e.g., "2B users, 50 searches/day/user")

    Returns:
        dict with scale analysis
    """
    # Simple mock analysis - in real agent, would do detailed calculations
    analysis = {
        "requests_per_second": "~1.16M QPS (2B users * 50 searches / 86400 seconds)",
        "storage_per_day": "~500 TB/day for search logs",
        "bandwidth": "~5 Tbps for global traffic",
        "infrastructure": {
            "data_centers": "10+ regions globally for low latency",
            "servers": "~100K+ servers for compute",
            "recommendation": "Use CDN, edge caching, and multi-region deployment",
        },
    }

    return {
        "success": True,
        "skill": "analyze_scale_requirements",
        "scenario": scenario,
        "analysis": analysis,
        "message": f"Scale analysis for: {scenario}",
    }


# Skill 2: Design Distributed Systems
def design_distributed_systems(use_case: str) -> dict:
    """
    Suggest distributed system architecture patterns.

    This is SKILL 2: Design Distributed Systems
    Use for: consistency models, replication, sharding, consensus algorithms

    Args:
        use_case: Description of what's needed (e.g., "global state management")

    Returns:
        dict with distributed system design suggestions
    """
    # Simple mock recommendations
    suggestions = {
        "consistency": [
            "Strong consistency with Paxos/Raft for critical data",
            "Eventual consistency with CRDTs for high availability",
            "Read-your-writes for user sessions",
        ],
        "replication": [
            "Multi-region active-active for disaster recovery",
            "Leader-follower for read scalability",
            "Quorum-based writes for durability",
        ],
        "sharding": [
            "Consistent hashing for load distribution",
            "Range-based sharding for time-series data",
            "Geographic sharding for data locality",
        ],
        "patterns": [
            "CQRS for read/write separation",
            "Event sourcing for audit trail",
            "Saga pattern for distributed transactions",
        ],
    }

    return {
        "success": True,
        "skill": "design_distributed_systems",
        "use_case": use_case,
        "suggestions": suggestions,
        "message": f"Distributed system design for: {use_case}",
    }


# Create the Google system design agent
root_agent = Agent(
    name="google_system_design_agent",
    model=os.getenv("AGENT_MODEL", "gemini-2.0-flash-exp"),
    description="Google system design interview expert for massive scale and distributed systems",
    instruction="""You are a Google system design interview expert with two specialized skills:

1. ANALYZE SCALE REQUIREMENTS: Use analyze_scale_requirements for billion-user scale calculations
2. DESIGN DISTRIBUTED SYSTEMS: Use design_distributed_systems for distributed architecture patterns

Use these tools to help evaluate large-scale system designs.""",
    tools=[analyze_scale_requirements, design_distributed_systems],
)

# Define custom agent card with 2 explicit skills
agent_card = AgentCard(
    name="google_system_design_agent",
    url="http://localhost:8003",
    description="Google system design interview expert for massive scale and distributed systems",
    version="1.0.0",
    capabilities={},
    skills=[
        AgentSkill(
            id="analyze_scale_requirements",
            name="Analyze Scale Requirements",
            description=(
                "Analyzes requirements for billion-user scale systems with "
                "QPS, storage, and infrastructure planning"
            ),
            tags=["scale", "billions", "infrastructure"],
        ),
        AgentSkill(
            id="design_distributed_systems",
            name="Design Distributed Systems",
            description=(
                "Suggests distributed system patterns including consistency, "
                "replication, sharding, and consensus"
            ),
            tags=["distributed", "consistency", "replication"],
        ),
    ],
    defaultInputModes=["text/plain"],
    defaultOutputModes=["text/plain"],
    supportsAuthenticatedExtendedCard=False,
)

# Expose agent via A2A protocol with custom agent card
a2a_app = to_a2a(root_agent, port=8003, agent_card=agent_card)
