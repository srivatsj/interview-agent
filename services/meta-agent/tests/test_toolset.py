import json
import sys
from pathlib import Path

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
if str(PACKAGE_ROOT) not in sys.path:
    sys.path.insert(0, str(PACKAGE_ROOT))

from meta_agent.toolset import MetaAgentToolset  # noqa: E402


def test_get_phases_plan_first() -> None:
    toolset = MetaAgentToolset()

    phases = toolset.get_phases()

    assert phases[0]["id"] == "plan_and_scope"
    assert len(phases) >= 6


def test_get_context_returns_guidance() -> None:
    toolset = MetaAgentToolset()

    context = toolset.get_context("plan_and_scope")

    assert "aligning on the interview plan" in context.lower()


def test_evaluate_advances_on_sufficient_keywords() -> None:
    toolset = MetaAgentToolset()
    history = [
        {
            "role": "user",
            "content": "My plan covers our approach, architecture, and components sequencing.",
        }
    ]

    result = toolset.evaluate("plan_and_scope", history)

    assert result["decision"] == "next_phase"
    assert result["score"] >= 6


def test_evaluate_identifies_missing_topics() -> None:
    toolset = MetaAgentToolset()
    history = [{"role": "user", "content": "We will start soon."}]

    result = toolset.evaluate("plan_and_scope", history)

    assert result["decision"] == "continue"
    assert "plan" in json.dumps(result["gaps"]).lower()


def test_evaluate_phase_aliases_to_evaluate() -> None:
    toolset = MetaAgentToolset()
    history = [
        {
            "role": "user",
            "content": "Our plan covers the architecture components and the rollout phases.",
        }
    ]

    result = toolset.evaluate_phase("plan_and_scope", history)

    assert result["decision"] == "next_phase"
