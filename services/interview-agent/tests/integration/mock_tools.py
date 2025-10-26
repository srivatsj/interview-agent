"""Mock tools for integration testing with reduced phases to avoid API quota issues."""


class MockAmazonTools:
    """Mock Amazon tools with only 2 phases for fast testing."""

    def get_phases(self):
        """Return 2 phases instead of 6."""
        return [
            {"id": "clarification", "name": "Clarification"},
            {"id": "design", "name": "Design"},
        ]

    def get_context(self, phase_id: str) -> str:
        """Get context for phase."""
        contexts = {
            "clarification": "Discuss scale, users, QPS, latency, availability",
            "design": "Discuss database, schema, indexing, sharding, load balancer, cache",
        }
        return contexts.get(phase_id, "Discuss system design")

    def evaluate(self, phase_id: str, conversation_history: list[dict]) -> dict:
        """Evaluate phase completion based on keywords."""
        keywords = {
            "clarification": ["scale", "users", "qps", "latency", "availability"],
            "design": ["database", "schema", "indexing", "sharding", "cache"],
        }

        phase_keywords = keywords.get(phase_id, [])
        if not phase_keywords:
            return {"decision": "next_phase", "score": 10}

        # Extract all text from conversation
        conversation_text = " ".join(
            [msg.get("content", "").lower() for msg in conversation_history]
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
