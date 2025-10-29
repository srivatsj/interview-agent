"""Google-specific system design interview tooling."""

from __future__ import annotations

import logging
from typing import Any, Iterable

from .base import InterviewToolset

logger = logging.getLogger(__name__)


class GoogleSystemDesignToolset(InterviewToolset):
    """Provides Google-flavoured system design phases, context, and evaluation."""

    _PHASES: list[dict[str, str]] = [
        {
            "id": "plan_and_scope",
            "name": "Plan & High-Level Scope",
        },
        {
            "id": "requirements_alignment",
            "name": "Requirements Alignment",
        },
        {
            "id": "architecture_blueprint",
            "name": "Architecture Blueprint",
        },
        {
            "id": "capacity_strategy",
            "name": "Capacity & Performance",
        },
        {
            "id": "data_platform",
            "name": "Data & Storage Strategy",
        },
        {
            "id": "reliability_review",
            "name": "Reliability & Trade-offs",
        },
    ]

    _PHASE_CONTEXTS: dict[str, str] = {
        "plan_and_scope": (
            "Begin by aligning on the interview plan and the system's high-level outline.\n"
            "- Summarise user journeys, success metrics, and top-level requirements.\n"
            "- Sketch primary components and request flow at a birds-eye view.\n"
            "- Confirm the phase sequence so interviewer and candidate stay synchronized."
        ),
        "requirements_alignment": (
            "Clarify the detailed requirements before designing internals.\n"
            "- Functional expectations, API capabilities, and differentiators.\n"
            "- Non-functional targets: latency, availability, SLOs, and compliance.\n"
            "- Operational constraints such as rollout timelines or dependencies."
        ),
        "architecture_blueprint": (
            "Present the end-to-end architecture once the plan is locked in.\n"
            "- Walk through request handling across services and data stores.\n"
            "- Distinguish stateless vs stateful components and critical dependencies.\n"
            "- Tie each decision back to the agreed plan and requirements."
        ),
        "capacity_strategy": (
            "Outline how the system meets scale and performance goals.\n"
            "- Quantify DAU/WAU, peak QPS, and regional distribution.\n"
            "- Describe autoscaling, caching strategy, and bottleneck mitigation.\n"
            "- Highlight latency budgets, rate-limiting, and CDN/edge considerations."
        ),
        "data_platform": (
            "Detail the data strategy supporting the design.\n"
            "- Storage engines, schema design, and transactional vs analytical paths.\n"
            "- Data lifecycle, retention, and privacy/compliance guardrails.\n"
            "- Indexing, partitioning, and replication to satisfy scale and resilience."
        ),
        "reliability_review": (
            "Stress-test the design and document trade-offs before closing.\n"
            "- Enumerate failure domains, redundancy, and disaster recovery plans.\n"
            "- Explain observability (metrics, logs, traces) and alerting workflows.\n"
            "- Call out explicit trade-offs, risks, and follow-up actions."
        ),
    }

    _EVALUATION_KEYWORDS: dict[str, list[str]] = {
        "plan_and_scope": [
            "plan",
            "approach",
            "architecture",
            "component",
            "phase",
        ],
        "requirements_alignment": [
            "requirements",
            "latency",
            "availability",
            "slo",
            "metric",
        ],
        "architecture_blueprint": [
            "service",
            "flow",
            "request",
            "api",
            "component",
        ],
        "capacity_strategy": [
            "qps",
            "scale",
            "traffic",
            "autoscale",
            "latency",
        ],
        "data_platform": [
            "database",
            "storage",
            "schema",
            "replication",
            "partition",
        ],
        "reliability_review": [
            "failure",
            "redundancy",
            "monitoring",
            "alert",
            "trade-off",
        ],
    }

    @classmethod
    def get_interview_type(cls) -> str:
        """Return the interview type this toolset supports."""
        return "system_design"

    def get_phases(self) -> list[dict[str, str]]:
        """Return the ordered phases."""
        logger.info("GoogleSystemDesignToolset.get_phases invoked")
        return list(self._PHASES)

    def get_context(self, phase_id: str) -> str:
        """Return context string for a phase."""
        logger.info("GoogleSystemDesignToolset.get_context(%s)", phase_id)
        return self._PHASE_CONTEXTS.get(
            phase_id,
            "Guide the candidate through Google-style system design best practices.",
        )

    def get_question(self, candidate_info: dict[str, Any]) -> str:
        """Generate an interview question based on candidate background."""
        logger.info("GoogleSystemDesignToolset.get_question(candidate_info=%s)", candidate_info)

        years_exp = candidate_info.get("years_experience", 0)
        domain = candidate_info.get("domain", "distributed systems")

        # Tailor question complexity based on experience
        if years_exp >= 5:
            return (
                f"Given your {years_exp} years of experience in {domain}, "
                "let's design a distributed system: Design a real-time collaborative "
                "document editing service like Google Docs. The system should support "
                "millions of concurrent users editing documents simultaneously. "
                "Walk me through your high-level architecture and design decisions."
            )
        elif years_exp >= 2:
            return (
                f"With your {years_exp} years of experience in {domain}, "
                "design a URL shortening service like bit.ly that can handle "
                "millions of requests per day. Start with the high-level architecture "
                "and explain your key design choices."
            )
        else:
            return (
                "Let's design a simple key-value cache service similar to Redis. "
                "The service should support GET and SET operations with TTL support. "
                "Walk me through your design approach starting with the core components."
            )

    def evaluate(
        self,
        phase_id: str,
        conversation_history: Iterable[dict[str, Any]],
    ) -> dict[str, Any]:
        """Evaluate coverage for a phase based on conversation."""
        logger.info("GoogleSystemDesignToolset.evaluate(%s) invoked", phase_id)
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

    def evaluate_phase(
        self,
        phase_id: str,
        conversation_history: Iterable[dict[str, Any]],
    ) -> dict[str, Any]:
        """Compatibility shim matching the on-service interface."""
        return self.evaluate(phase_id, conversation_history)

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
