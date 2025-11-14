"""
Meta System Design Interview Agent - Exposed via A2A Protocol

This agent has 2 skills:
1. Design Social Graph - Architecture for social connections and feeds
2. Optimize Performance - Performance optimization strategies
"""

import os

from a2a.types import AgentCard, AgentSkill
from dotenv import load_dotenv
from google.adk.a2a.utils.agent_to_a2a import to_a2a
from google.adk.agents import Agent

# Load environment variables from .env file
load_dotenv()


# Skill 1: Design Social Graph
def design_social_graph(scenario: str) -> dict:
    """
    Design social graph architecture for connections and feeds.

    This is SKILL 1: Design Social Graph
    Use for: friend relationships, news feeds, follower systems

    Args:
        scenario: Description of the scenario (e.g., "3B users, avg 500 friends")

    Returns:
        dict with social graph design recommendations
    """
    # Simple mock design - in real agent, would provide detailed architecture
    design = {
        "graph_storage": {
            "adjacency_list": "Store friend lists in NoSQL (DynamoDB/Cassandra)",
            "graph_db": "Use graph database (Neo4j) for complex queries",
            "sharding": "Shard by user_id for horizontal scaling",
        },
        "news_feed": {
            "ranking": "ML-based ranking for personalized feeds",
            "caching": "Redis cache for recent feed items per user",
            "fan_out": "Fan-out on write for active users, pull on read for celebrities",
        },
        "performance": {
            "qps": "~300K reads/sec for feed generation",
            "latency": "<100ms P99 for feed load",
            "recommendation": "Pre-compute feeds, use CDN for media content",
        },
    }

    return {
        "success": True,
        "skill": "design_social_graph",
        "scenario": scenario,
        "design": design,
        "message": f"Social graph design for: {scenario}",
    }


# Skill 2: Optimize Performance
def optimize_performance(requirement: str) -> dict:
    """
    Suggest performance optimization strategies.

    This is SKILL 2: Optimize Performance
    Use for: latency reduction, throughput improvement, resource optimization

    Args:
        requirement: What needs optimization (e.g., "reduce API latency")

    Returns:
        dict with optimization strategies
    """
    # Simple mock strategies
    strategies = {
        "caching": [
            "Multi-layer caching (L1: in-memory, L2: Redis, L3: CDN)",
            "Cache invalidation with TTL and event-driven updates",
            "Edge caching for static content",
        ],
        "database": [
            "Read replicas for read-heavy workloads",
            "Connection pooling to reduce overhead",
            "Query optimization and indexing",
            "Denormalization for faster reads",
        ],
        "architecture": [
            "Async processing with message queues",
            "Load balancing across multiple regions",
            "Circuit breakers for fault tolerance",
            "Rate limiting and request throttling",
        ],
        "monitoring": [
            "Real-time metrics with Prometheus/Grafana",
            "Distributed tracing for bottleneck identification",
            "Auto-scaling based on traffic patterns",
        ],
    }

    return {
        "success": True,
        "skill": "optimize_performance",
        "requirement": requirement,
        "strategies": strategies,
        "message": f"Performance optimization for: {requirement}",
    }


# Create the Meta system design agent
root_agent = Agent(
    name="meta_system_design_agent",
    model=os.getenv("AGENT_MODEL", "gemini-2.0-flash-exp"),
    description=(
        "Meta system design interview expert for social graphs and performance optimization"
    ),
    instruction="""You are a Meta system design interview expert with two specialized skills:

1. DESIGN SOCIAL GRAPH: Use design_social_graph for social connections and feed architecture
2. OPTIMIZE PERFORMANCE: Use optimize_performance for latency and throughput optimization

Use these tools to help evaluate social media system designs.""",
    tools=[design_social_graph, optimize_performance],
)

# Define custom agent card with 2 explicit skills
agent_card = AgentCard(
    name="meta_system_design_agent",
    url="http://localhost:8004",
    description=(
        "Meta system design interview expert for social graphs and performance optimization"
    ),
    version="1.0.0",
    capabilities={},
    skills=[
        AgentSkill(
            id="design_social_graph",
            name="Design Social Graph",
            description=(
                "Designs social graph architecture for friend connections, "
                "news feeds, and follower systems"
            ),
            tags=["social-graph", "feeds", "connections"],
        ),
        AgentSkill(
            id="optimize_performance",
            name="Optimize Performance",
            description=(
                "Suggests performance optimization strategies for latency, "
                "throughput, and resource efficiency"
            ),
            tags=["performance", "optimization", "latency"],
        ),
    ],
    defaultInputModes=["text/plain"],
    defaultOutputModes=["text/plain"],
    supportsAuthenticatedExtendedCard=False,
)

# Expose agent via A2A protocol with custom agent card
a2a_app = to_a2a(root_agent, port=8004, agent_card=agent_card)
