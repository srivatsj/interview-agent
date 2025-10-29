"""Coding interview toolset."""

from __future__ import annotations

import logging
from typing import Any, Iterable

from .base import InterviewToolset

logger = logging.getLogger(__name__)


class CodingToolset(InterviewToolset):
    """Provides coding interview phases, context, and evaluation."""

    _PHASES: list[dict[str, str]] = [
        {"id": "problem_understanding", "name": "Problem Understanding"},
        {"id": "solution_design", "name": "Solution Design & Approach"},
        {"id": "implementation", "name": "Code Implementation"},
        {"id": "testing_edge_cases", "name": "Testing & Edge Cases"},
        {"id": "optimization", "name": "Time/Space Optimization"},
    ]

    _PHASE_CONTEXTS: dict[str, str] = {
        "problem_understanding": (
            "Ensure the candidate understands the problem fully.\n"
            "- Clarify input/output format and constraints.\n"
            "- Discuss example test cases and edge cases.\n"
            "- Confirm understanding before proceeding to solution."
        ),
        "solution_design": (
            "Have the candidate explain their approach before coding.\n"
            "- Outline the algorithm or data structures to use.\n"
            "- Discuss time and space complexity expectations.\n"
            "- Consider multiple approaches and trade-offs."
        ),
        "implementation": (
            "Candidate implements the solution in their preferred language.\n"
            "- Write clean, readable code with good variable names.\n"
            "- Handle edge cases and boundary conditions.\n"
            "- Explain logic while coding."
        ),
        "testing_edge_cases": (
            "Verify the solution works correctly.\n"
            "- Walk through example inputs manually.\n"
            "- Identify and test edge cases (empty input, single element, etc.).\n"
            "- Debug any issues found."
        ),
        "optimization": (
            "Analyze and optimize the solution if needed.\n"
            "- Calculate actual time and space complexity.\n"
            "- Discuss potential optimizations.\n"
            "- Trade-offs between readability and performance."
        ),
    }

    _EVALUATION_KEYWORDS: dict[str, list[str]] = {
        "problem_understanding": [
            "input",
            "output",
            "constraint",
            "edge case",
            "example",
        ],
        "solution_design": [
            "algorithm",
            "data structure",
            "approach",
            "complexity",
            "trade-off",
        ],
        "implementation": ["function", "loop", "condition", "variable", "return"],
        "testing_edge_cases": ["test", "edge", "case", "debug", "verify"],
        "optimization": [
            "optimize",
            "complexity",
            "efficient",
            "performance",
            "space",
        ],
    }

    @classmethod
    def get_interview_type(cls) -> str:
        """Return the interview type this toolset supports."""
        return "coding"

    def get_phases(self) -> list[dict[str, str]]:
        """Return the ordered phases."""
        logger.info("CodingToolset.get_phases invoked")
        return list(self._PHASES)

    def get_context(self, phase_id: str) -> str:
        """Return context string for a phase."""
        logger.info("CodingToolset.get_context(%s)", phase_id)
        return self._PHASE_CONTEXTS.get(
            phase_id,
            "Guide the candidate through coding best practices.",
        )

    def get_question(self, candidate_info: dict[str, Any]) -> str:
        """Generate a coding question based on candidate background."""
        logger.info("CodingToolset.get_question(candidate_info=%s)", candidate_info)

        years_exp = candidate_info.get("years_experience", 0)
        domain = candidate_info.get("domain", "software engineering")

        # Tailor question difficulty based on experience
        if years_exp >= 5:
            return (
                f"Given your {years_exp} years of experience in {domain}, "
                "here's a challenging problem: Design and implement an LRU (Least Recently Used) "
                "cache that supports get(key) and put(key, value) operations, both in O(1) time. "
                "Explain your approach, implement it, and discuss the data structures you'll use."
            )
        elif years_exp >= 2:
            return (
                f"With your {years_exp} years of experience, solve this: "
                "Given an array of integers and a target sum, find two numbers in the array "
                "that add up to the target. Return their indices. Explain your approach, "
                "implement it, and analyze the time and space complexity."
            )
        else:
            return (
                "Let's start with a fundamental problem: Write a function to reverse a string. "
                "Explain your approach, implement it, and discuss any edge cases you should handle."
            )

    def evaluate(
        self,
        phase_id: str,
        conversation_history: Iterable[dict[str, Any]],
    ) -> dict[str, Any]:
        """Evaluate coverage for a phase based on conversation."""
        logger.info("CodingToolset.evaluate(%s) invoked", phase_id)
        keywords = self._EVALUATION_KEYWORDS.get(phase_id, [])
        coverage = self._coverage(conversation_history, keywords)

        if coverage >= 0.6:
            return {
                "decision": "next_phase",
                "score": int(coverage * 10),
                "message": "Phase objectives satisfied, proceed.",
            }

        missing = self._missing_keywords(conversation_history, keywords)
        followups = (
            "Expand on: " + ", ".join(missing[:2]) if missing else "Clarify remaining open points."
        )
        return {
            "decision": "continue",
            "score": int(coverage * 10),
            "gaps": missing,
            "followup_questions": followups,
        }

    def _coverage(
        self,
        conversation_history: Iterable[dict[str, Any]],
        keywords: list[str],
    ) -> float:
        if not keywords:
            return 1.0
        text = self._flatten_conversation(conversation_history)
        hits = sum(1 for keyword in keywords if keyword in text)
        return hits / len(keywords)

    def _missing_keywords(
        self,
        conversation_history: Iterable[dict[str, Any]],
        keywords: list[str],
    ) -> list[str]:
        text = self._flatten_conversation(conversation_history)
        return [keyword for keyword in keywords if keyword not in text]

    @staticmethod
    def _flatten_conversation(
        conversation_history: Iterable[dict[str, Any]],
    ) -> str:
        snippets: list[str] = []
        for message in conversation_history:
            content = message.get("content")
            if isinstance(content, str):
                snippets.append(content.lower())
        return " ".join(snippets)
