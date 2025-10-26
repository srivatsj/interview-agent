"""Tests for AmazonSystemDesignTools"""

from interview_agent.interview_types.system_design.tools.amazon_tools import (
    AmazonSystemDesignTools,
)


class TestAmazonSystemDesignTools:
    """Test Amazon system design tools"""

    def test_get_phases(self):
        """Test get_phases returns correct phases"""
        tools = AmazonSystemDesignTools()

        phases = tools.get_phases()

        assert len(phases) == 5
        assert phases[0]["id"] == "problem_clarification"
        assert phases[-1]["id"] == "hld"

    def test_get_context_for_data_design(self):
        """Test get_context returns context for data design"""
        tools = AmazonSystemDesignTools()

        context = tools.get_context("data_design")

        assert "database" in context.lower()
        assert "schema" in context.lower()

    def test_get_context_for_unknown_phase(self):
        """Test get_context handles unknown phase"""
        tools = AmazonSystemDesignTools()

        context = tools.get_context("unknown_phase")

        assert context == "Discuss system design"

    def test_evaluate_with_good_coverage(self):
        """Test evaluate returns next_phase with good keyword coverage"""
        tools = AmazonSystemDesignTools()
        conversation = [
            {
                "role": "user",
                "content": (
                    "We need to handle 10k QPS with high availability "
                    "for millions of users with low latency"
                ),
            },
        ]

        result = tools.evaluate("problem_clarification", conversation)

        assert result["decision"] == "next_phase"
        assert result["score"] >= 6  # At least 60% coverage

    def test_evaluate_with_poor_coverage(self):
        """Test evaluate returns continue with poor keyword coverage"""
        tools = AmazonSystemDesignTools()
        conversation = [
            {"role": "user", "content": "I think we should use a database"},
        ]

        result = tools.evaluate("problem_clarification", conversation)

        assert result["decision"] == "continue"
        assert result["score"] < 6  # Less than 60% coverage
        assert "gaps" in result
        assert "followup_questions" in result

    def test_evaluate_with_empty_conversation(self):
        """Test evaluate handles empty conversation"""
        tools = AmazonSystemDesignTools()

        result = tools.evaluate("data_design", [])

        assert result["decision"] == "continue"
        assert result["score"] == 0

    def test_calculate_coverage(self):
        """Test coverage calculation"""
        tools = AmazonSystemDesignTools()

        conversation = [
            {"role": "user", "content": "We need indexing and sharding"},
            {"role": "assistant", "content": "Good"},
        ]
        keywords = ["database", "index", "shard", "replication"]

        coverage = tools._calculate_coverage(conversation, keywords)

        # Should find "index" (from "indexing") and "shard" (from "sharding")
        assert coverage == 0.5  # 2 out of 4 keywords

    def test_find_missing_keywords(self):
        """Test finding keywords not mentioned in conversation"""
        tools = AmazonSystemDesignTools()

        conversation = [
            {"role": "user", "content": "We will use database with indexing"},
        ]
        keywords = ["database", "index", "shard", "replication"]

        missing = tools._find_missing_keywords(conversation, keywords)

        assert "shard" in missing
        assert "replication" in missing
        assert "database" not in missing
        assert "index" not in missing
