"""Default local implementation for system design interviews.

Used as fallback when no remote A2A agent is available for a company.
Contains keyword-based phase evaluation - simple but functional.
"""

import logging

logger = logging.getLogger(__name__)


# In-memory phase data
PHASES = [
    {"id": "get_problem", "name": "Problem Statement"},
    {"id": "problem_clarification", "name": "Problem Clarification"},
    {"id": "requirements", "name": "Requirements"},
    {"id": "data_design", "name": "Data Design"},
    {"id": "api_design", "name": "API Design"},
    {"id": "hld", "name": "High Level Design"},
]

# Context for each phase
PHASE_CONTEXTS = {
    "get_problem": """
        Present the system design problem to the candidate:
        - Describe the system to be designed (e.g., "Design a URL shortener like bit.ly")
        - Keep it brief and clear
        - Wait for the candidate to acknowledge before moving to next phase
        - Once the candidate understands the problem, mark this phase complete
    """,
    "problem_clarification": """
        Clarify the problem by asking about:
        - Scale (DAU, QPS, data volume)
        - Geographic distribution
        - Core features vs nice-to-have
        - Latency and availability requirements
    """,
    "requirements": """
        Define requirements:
        - Functional: What the system does (create, read, update, delete operations)
        - Non-functional: Scalability, availability, consistency, latency
        - Constraints: Budget, timeline, existing systems
    """,
    "data_design": """
        Design data layer:
        - Database choice (SQL vs NoSQL)
        - Schema (tables, fields, relationships)
        - Indexing strategy
        - Sharding/partitioning
        - Replication
    """,
    "api_design": """
        Design APIs:
        - REST/gRPC endpoints
        - Request/response formats
        - Authentication/authorization
        - Rate limiting
    """,
    "hld": """
        High-level architecture:
        - System components (services, databases, caches)
        - Load balancers, CDN
        - Message queues
        - Data flow between components
    """,
}

# Evaluation criteria (keywords to check for each phase)
EVALUATION_KEYWORDS = {
    "get_problem": ["understand", "clear", "ready", "yes", "got it"],
    "problem_clarification": ["qps", "scale", "users", "latency", "availability"],
    "requirements": ["functional", "non-functional", "consistency", "scalability"],
    "data_design": ["database", "schema", "index", "shard", "replication"],
    "api_design": ["api", "endpoint", "rest", "grpc", "auth"],
    "hld": ["load balancer", "cache", "queue", "component", "architecture"],
}


class DefaultSystemDesignTools:
    """Default local system design interview tools.

    This is a simple, keyword-based implementation used when:
    - No remote agent exists for a company
    - Remote agent is unavailable
    - Testing/development without remote services
    """

    def __init__(self):
        """Initialize default tools."""
        self._candidate_info = {}

    async def get_question(self) -> str:
        """Get an interview question tailored to candidate background.

        Returns:
            Interview question based on candidate experience
        """
        logger.info("Generating interview question")

        # Use candidate info if available
        years_experience = self._candidate_info.get("years_experience", 3)

        # Generate appropriate question based on experience
        if years_experience < 2:
            return (
                "Design a URL shortening service like bit.ly. "
                "Focus on the basic functionality: creating short URLs and redirecting users."
            )
        elif years_experience < 5:
            return (
                "Design a URL shortening service like bit.ly that can handle millions of users. "
                "Consider scalability, data storage, and how to generate unique short URLs."
            )
        else:
            return (
                "Design a highly scalable URL shortening service like bit.ly that can handle "
                "billions of URLs and high read/write throughput. Consider sharding, caching, "
                "rate limiting, analytics, and how to handle geographic distribution."
            )

    async def get_phases(self) -> list[dict]:
        """Get interview phases in order"""
        logger.info("Getting default system design phases")
        return PHASES

    async def get_context(self, phase_id: str) -> str:
        """Get context/topics for current phase"""
        logger.info(f"Getting context for phase: {phase_id}")
        return PHASE_CONTEXTS.get(phase_id, "Discuss system design")

    async def evaluate_phase(self, phase_id: str, conversation_history: list[dict]) -> dict:
        """Evaluate phase completion and decide next action"""
        logger.info(f"Evaluating phase: {phase_id}")

        conversation = conversation_history

        # Simple keyword-based evaluation
        keywords = EVALUATION_KEYWORDS.get(phase_id, [])
        coverage = self._calculate_coverage(conversation, keywords)

        # Decide based on coverage
        if coverage >= 0.6:  # 60% keywords mentioned
            return {
                "decision": "next_phase",
                "score": int(coverage * 10),
                "message": f"Good coverage of {phase_id}!",
            }
        else:
            missing = self._find_missing_keywords(conversation, keywords)
            return {
                "decision": "continue",
                "score": int(coverage * 10),
                "gaps": missing,
                "followup_questions": f"Let's discuss: {', '.join(missing[:2])}",
            }

    def _calculate_coverage(self, conversation: list[dict], keywords: list[str]) -> float:
        """Calculate keyword coverage in conversation"""
        if not keywords:
            return 1.0

        # Combine all user messages
        text = " ".join(
            msg.get("content", "").lower() for msg in conversation if msg.get("role") == "user"
        )

        # Count how many keywords are mentioned
        mentioned = sum(1 for keyword in keywords if keyword.lower() in text)
        return mentioned / len(keywords)

    def _find_missing_keywords(self, conversation: list[dict], keywords: list[str]) -> list[str]:
        """Find keywords not mentioned in conversation"""
        text = " ".join(
            msg.get("content", "").lower() for msg in conversation if msg.get("role") == "user"
        )

        return [keyword for keyword in keywords if keyword.lower() not in text]
