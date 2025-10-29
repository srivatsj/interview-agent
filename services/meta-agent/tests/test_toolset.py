import json

from meta_agent.tools.design_toolset import MetaAgentToolset


def test_get_interview_type_returns_system_design() -> None:
    interview_type = MetaAgentToolset.get_interview_type()

    assert interview_type == "system_design"


def test_get_phases_plan_first() -> None:
    toolset = MetaAgentToolset()

    phases = toolset.get_phases()

    assert phases[0]["id"] == "plan_and_scope"
    assert len(phases) >= 6


def test_get_context_returns_guidance() -> None:
    toolset = MetaAgentToolset()

    context = toolset.get_context("plan_and_scope")

    assert "aligning on the interview plan" in context.lower()


def test_get_question_tailors_to_experience() -> None:
    toolset = MetaAgentToolset()

    # Test senior candidate
    senior_question = toolset.get_question({"years_experience": 7, "domain": "cloud systems"})
    assert "7 years" in senior_question
    assert "cloud systems" in senior_question
    assert len(senior_question) > 0

    # Test mid-level candidate
    mid_question = toolset.get_question({"years_experience": 3, "domain": "web development"})
    assert "3 years" in mid_question
    assert len(mid_question) > 0

    # Test junior candidate
    junior_question = toolset.get_question({"years_experience": 1})
    assert len(junior_question) > 0


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
