"""LangGraph meta agent toolset mirroring Google system-design capabilities."""

from __future__ import annotations

import logging
from typing import Any, Iterable

logger = logging.getLogger(__name__)


class MetaAgentToolset:
    """Provides Google-style interview skills for the LangGraph meta agent."""

    _PHASES: list[dict[str, str]] = [
        {"id": "plan_and_scope", "name": "Plan & High-Level Scope"},
        {"id": "requirements_alignment", "name": "Requirements Alignment"},
        {"id": "architecture_blueprint", "name": "Architecture Blueprint"},
        {"id": "capacity_strategy", "name": "Capacity & Performance"},
        {"id": "data_platform", "name": "Data & Storage Strategy"},
        {"id": "reliability_review", "name": "Reliability & Trade-offs"},
    ]

    _PHASE_CONTEXTS: dict[str, str] = {
        "plan_and_scope": (
            "Begin by aligning on the interview plan and the system's high-level outline.\n"
            "- Summarise user journeys, success metrics, and top-level requirements.\n"
            "- Sketch primary components and request flow at a birds-eye view.\n"
            "- Confirm the phase sequence so interviewer and candidate stay synchronised."
        ),
        "requirements_alignment": (
            "Clarify detailed functional and non-functional requirements before designing "
            "internals.\n"
            "- Capture API capabilities, differentiators, and user experience expectations.\n"
            "- Quantify latency, availability, SLOs, and compliance targets.\n"
            "- Surface operational constraints such as rollout timelines or dependencies."
        ),
        "architecture_blueprint": (
            "Present the end-to-end architecture once the plan is locked in.\n"
            "- Walk through request handling across services and data stores.\n"
            "- Distinguish stateless versus stateful components and critical dependencies.\n"
            "- Tie each decision back to the agreed plan and requirements."
        ),
        "capacity_strategy": (
            "Outline how the system meets scale and performance goals.\n"
            "- Quantify DAU/WAU, regional distribution, and peak QPS.\n"
            "- Describe autoscaling, caching strategy, and bottleneck mitigation.\n"
            "- Highlight latency budgets, rate limiting, and CDN or edge considerations."
        ),
        "data_platform": (
            "Detail the data strategy supporting the design.\n"
            "- Storage engines, schema design, and transactional versus analytical paths.\n"
            "- Data lifecycle, retention, and privacy or compliance guardrails.\n"
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
        "plan_and_scope": ["plan", "approach", "architecture", "component", "phase"],
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
        "capacity_strategy": ["qps", "scale", "traffic", "autoscale", "latency"],
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

    def get_phases(self) -> list[dict[str, str]]:
        logger.info("MetaAgentToolset.get_phases invoked")
        return list(self._PHASES)

    def get_context(self, phase_id: str) -> str:
        logger.info("MetaAgentToolset.get_context(%s)", phase_id)
        return self._PHASE_CONTEXTS.get(
            phase_id,
            "Guide the candidate through system design best practices.",
        )

    def evaluate(
        self, phase_id: str, conversation_history: Iterable[dict[str, Any]]
    ) -> dict[str, Any]:
        logger.info("MetaAgentToolset.evaluate(%s) invoked", phase_id)
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
        self, phase_id: str, conversation_history: Iterable[dict[str, Any]]
    ) -> dict[str, Any]:
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
