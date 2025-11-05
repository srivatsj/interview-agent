"""Tests for DefaultSystemDesignTools"""

import pytest

from interview_orchestrator.interview_types.system_design.tools import DefaultSystemDesignTools


class TestDefaultSystemDesignTools:
    """Test default system design tools"""

    @pytest.mark.asyncio
    async def test_get_question(self):
        """Test get_question returns a question based on experience"""
        tools = DefaultSystemDesignTools()

        # Test with default experience (3 years)
        question = await tools.get_question()
        assert isinstance(question, str)
        assert len(question) > 0
        assert "URL shortening" in question or "url shortening" in question.lower()

    @pytest.mark.asyncio
    async def test_get_question_junior_experience(self):
        """Test get_question returns simpler question for junior candidates"""
        tools = DefaultSystemDesignTools()
        tools._candidate_info = {"years_experience": 1}

        question = await tools.get_question()
        assert "basic functionality" in question.lower()

    @pytest.mark.asyncio
    async def test_get_question_senior_experience(self):
        """Test get_question returns complex question for senior candidates"""
        tools = DefaultSystemDesignTools()
        tools._candidate_info = {"years_experience": 10}

        question = await tools.get_question()
        assert "billions" in question.lower() or "sharding" in question.lower()

    @pytest.mark.asyncio
    async def test_get_phases(self):
        """Test get_phases returns correct phases"""
        tools = DefaultSystemDesignTools()

        phases = await tools.get_phases()

        assert len(phases) == 5
        assert phases[0]["id"] == "problem_clarification"
        assert phases[1]["id"] == "requirements"
        assert phases[-1]["id"] == "hld"

    @pytest.mark.asyncio
    async def test_get_context_for_data_design(self):
        """Test get_context returns context for data design"""
        tools = DefaultSystemDesignTools()

        context = await tools.get_context("data_design")

        assert "database" in context.lower()
        assert "schema" in context.lower()

    @pytest.mark.asyncio
    async def test_get_context_for_unknown_phase(self):
        """Test get_context handles unknown phase"""
        tools = DefaultSystemDesignTools()

        context = await tools.get_context("unknown_phase")

        assert context == "Discuss system design"

    @pytest.mark.asyncio
    async def test_evaluate_with_good_coverage(self):
        """Test evaluate returns next_phase with good keyword coverage"""
        tools = DefaultSystemDesignTools()
        conversation = [
            {
                "role": "user",
                "content": (
                    "We need to handle 10k QPS with high availability "
                    "for millions of users with low latency"
                ),
            },
        ]

        result = await tools.evaluate_phase("problem_clarification", conversation)

        assert result["decision"] == "next_phase"
        assert result["score"] >= 6  # At least 60% coverage

    @pytest.mark.asyncio
    async def test_evaluate_with_poor_coverage(self):
        """Test evaluate returns continue with poor keyword coverage"""
        tools = DefaultSystemDesignTools()
        conversation = [
            {"role": "user", "content": "I think we should use a database"},
        ]

        result = await tools.evaluate_phase("problem_clarification", conversation)

        assert result["decision"] == "continue"
        assert result["score"] < 6  # Less than 60% coverage
        assert "gaps" in result
        assert "followup_questions" in result

    @pytest.mark.asyncio
    async def test_evaluate_with_empty_conversation(self):
        """Test evaluate handles empty conversation"""
        tools = DefaultSystemDesignTools()

        result = await tools.evaluate_phase("data_design", [])

        assert result["decision"] == "continue"
        assert result["score"] == 0

    def test_calculate_coverage(self):
        """Test coverage calculation"""
        tools = DefaultSystemDesignTools()

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
        tools = DefaultSystemDesignTools()

        conversation = [
            {"role": "user", "content": "We will use database with indexing"},
        ]
        keywords = ["database", "index", "shard", "replication"]

        missing = tools._find_missing_keywords(conversation, keywords)

        assert "shard" in missing
        assert "replication" in missing
        assert "database" not in missing
        assert "index" not in missing
