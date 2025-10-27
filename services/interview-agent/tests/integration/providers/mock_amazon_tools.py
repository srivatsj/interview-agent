"""
Mock Amazon System Design Tools for fast integration testing.

Uses only 3 phases instead of 6 to speed up tests while still validating:
- Phase progression logic
- Multi-turn conversations
- Phase completion evaluation
- State management
"""


class MockAmazonSystemDesignTools:
    """Mock Amazon tools with 3 phases for fast testing."""

    def get_phases(self) -> list[dict]:
        """Return 3 phases instead of 6 for faster tests."""
        return [
            {"id": "clarification", "name": "Problem Clarification"},
            {"id": "design", "name": "System Design"},
            {"id": "tradeoffs", "name": "Trade-offs & Scale"},
        ]

    def get_context(self, phase_id: str) -> str:
        """Get context for each phase."""
        contexts = {
            "clarification": """
                Clarify the problem by asking about:
                - Scale (DAU, QPS, data volume)
                - Core features vs nice-to-have
                - Latency and availability requirements
            """,
            "design": """
                Design the system:
                - Database choice and schema
                - API design
                - Core architecture components
            """,
            "tradeoffs": """
                Discuss trade-offs and scaling:
                - Bottlenecks and solutions
                - Caching strategy
                - Load balancing and sharding
            """,
        }
        return contexts.get(phase_id, "Discuss system design")

    def evaluate(self, phase_id: str, conversation_history: list[dict]) -> dict:
        """Evaluate phase completion based on keywords."""
        keywords = {
            "clarification": ["scale", "users", "qps", "latency", "availability"],
            "design": ["database", "schema", "api", "architecture", "component"],
            "tradeoffs": ["cache", "load balance", "shard", "bottleneck", "scale"],
        }

        phase_keywords = keywords.get(phase_id, [])
        if not phase_keywords:
            return {"decision": "next_phase", "score": 10}

        # Extract text from conversation
        conversation_text = " ".join(
            [
                msg.get("content", "").lower()
                for msg in conversation_history
                if msg.get("role") == "user"
            ]
        )

        # Calculate coverage
        matched = sum(1 for kw in phase_keywords if kw in conversation_text)
        coverage = matched / len(phase_keywords) if phase_keywords else 1.0

        if coverage >= 0.6:  # 60% threshold
            return {
                "decision": "next_phase",
                "score": int(coverage * 10),
                "message": f"Good coverage of {phase_id}",
            }
        else:
            return {
                "decision": "continue",
                "score": int(coverage * 10),
                "gaps": [kw for kw in phase_keywords if kw not in conversation_text],
            }
