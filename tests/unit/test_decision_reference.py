"""Decision Reference 单测:构建 / 评分 / 风险融合 / 失败融合 / replay / context / WebUI。"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from maple_agent.agent_loop.models import AgentLoopContext, AgentLoopStatus
from maple_agent.decision_reference import (
    DecisionReferenceBuilder,
    DecisionReferenceValidator,
    DecisionRiskIntegrator,
    DecisionScorer,
    save_decision_reference_trace,
)
from maple_agent.environment_planning.models import (
    EnvironmentPlanningReference,
    GoalPriorityReference,
)
from maple_agent.events import EventBus
from maple_agent.failure_intelligence.models import (
    FailurePreventionReference,
)
from maple_agent.planning_optimizer.models import PlanningQualityScore
from maple_agent.runtime import RuntimeManager
from maple_agent.webui.app import create_app
from maple_agent.world_model.models import PredictedEnvironmentState


def _environment_reference(
    *,
    blocked: bool = False,
    adjustments: list[GoalPriorityReference] | None = None,
) -> EnvironmentPlanningReference:
    adjustments = adjustments or [
        GoalPriorityReference(
            goal_id="goal-1",
            suggested_priority=85,
            reason="环境有 NPC 可交互",
            opportunity_type="NPC_INTERACTION",
            confidence=0.9,
        )
    ]
    return EnvironmentPlanningReference(
        recommended_goals=[] if blocked else ["goal-1"],
        blocked_goals=["goal-1"] if blocked else [],
        priority_adjustments=adjustments,
        risk_notes=["[blocked] 高风险"] if blocked else [],
        opportunity_notes=["NPC_INTERACTION: 环境有 NPC 可交互"]
        if not blocked
        else [],
        confidence=0.3 if blocked else 0.9,
    )


def _failure_prevention(
    *,
    avoid: list[str] | None = None,
    warnings: list[str] | None = None,
    recovery: list[str] | None = None,
) -> FailurePreventionReference:
    return FailurePreventionReference(
        avoid_tasks=avoid or [],
        risk_warnings=warnings or [],
        recovery_points=recovery or [],
        prevention_notes=[],
        summary="test",
    )


def _world_prediction() -> PredictedEnvironmentState:
    return PredictedEnvironmentState(
        predicted_location="魔法密林",
        predicted_entities=["爱丽丝"],
        confidence=0.85,
        summary="预测位于 魔法密林",
    )


def _planning_quality() -> PlanningQualityScore:
    return PlanningQualityScore(
        planning_score=0.8,
        dependency_score=1.0,
        risk_score=0.8,
        experience_alignment=0.5,
        estimated_success_probability=0.8,
    )


def test_reference_build():
    builder = DecisionReferenceBuilder()
    reference = builder.build(
        environment_reference=_environment_reference(),
        world_prediction=_world_prediction(),
        failure_prevention=_failure_prevention(),
        planning_quality=_planning_quality(),
        goal_id="goal-1",
    )
    assert reference.recommended_options
    assert reference.recommended_options[0].action == "TALK"
    assert reference.recommended_options[0].target == "goal-1"
    assert reference.risk_level == "LOW"
    assert reference.environment_alignment == 0.9
    assert reference.planning_alignment == 0.8
    assert reference.reasoning
    assert any("世界预测" in reason for reason in reference.reasoning)


def test_high_risk_no_recommended():
    builder = DecisionReferenceBuilder()
    reference = builder.build(
        environment_reference=_environment_reference(blocked=True),
        failure_prevention=_failure_prevention(
            recovery=["recovery:task-3"],
        ),
        planning_quality=_planning_quality(),
        goal_id="goal-1",
    )
    assert reference.risk_level == "HIGH"
    assert reference.recommended_options == []
    assert reference.alternative_options
    assert any(
        option.recommendation == "alternative"
        for option in reference.alternative_options
    )


def test_scoring_formula():
    builder = DecisionReferenceBuilder()
    reference = builder.build(
        environment_reference=_environment_reference(),
        planning_quality=_planning_quality(),
        goal_id="goal-1",
    )
    score = DecisionScorer().score(
        reference=reference,
        historical_success=0.6,
    )
    # 0.3*0.9 + 0.3*0.8 + 0.2*1.0 + 0.2*0.6 = 0.83
    assert score.decision_score == 0.83
    assert score.risk_awareness == 1.0
    assert score.components["historical_success"] == 0.6


def test_risk_integration():
    integrator = DecisionRiskIntegrator()
    notes = integrator.integrate(
        environment_reference=_environment_reference(),
        failure_prevention=_failure_prevention(
            avoid=["task-3"],
            warnings=["task-3 失败概率 70%"],
            recovery=["recovery:task-3"],
        ),
    )
    assert notes.risk_level == "MEDIUM"
    assert "task-3" in notes.avoid_options
    assert notes.alternative_suggestions == ["recovery:task-3"]
    assert any("应避免任务" in note for note in notes.risk_notes)


def test_failure_integration():
    integrator = DecisionRiskIntegrator()
    notes = integrator.integrate(
        environment_reference=_environment_reference(),
        failure_prevention=_failure_prevention(
            avoid=["task-4"],
            warnings=["task-4 高风险"],
        ),
    )
    assert "task-4" in notes.avoid_options
    assert any("task-4 高风险" in note for note in notes.risk_notes)


def test_replay_generation(tmp_path):
    builder = DecisionReferenceBuilder()
    reference = builder.build(
        environment_reference=_environment_reference(),
        planning_quality=_planning_quality(),
        goal_id="goal-1",
    )
    score = DecisionScorer().score(
        reference=reference,
        historical_success=0.6,
    )
    notes = DecisionRiskIntegrator().integrate(
        environment_reference=_environment_reference(),
    )
    save_decision_reference_trace(
        tmp_path,
        "trace-replay",
        decision_reference=reference,
        score=score,
        risk_notes=notes.risk_notes,
    )
    replay = json.loads(
        (
            tmp_path
            / "trace-replay"
            / "decision_reference_trace.json"
        ).read_text(encoding="utf-8")
    )
    assert replay["schema_version"] == "1.0"
    assert replay["decision_reference"]["risk_level"] == "LOW"
    assert replay["decision_reference"]["recommended_options"]
    assert replay["score"]["decision_score"] > 0
    assert isinstance(replay["risk_notes"], list)


def test_validator():
    builder = DecisionReferenceBuilder()
    reference = builder.build(
        environment_reference=_environment_reference(),
        planning_quality=_planning_quality(),
        goal_id="goal-1",
    )
    score = DecisionScorer().score(reference=reference)
    result = DecisionReferenceValidator().validate(
        reference=reference,
        score=score,
    )
    assert result.valid is True


def test_context_integration():
    builder = DecisionReferenceBuilder()
    reference = builder.build(
        environment_reference=_environment_reference(),
        planning_quality=_planning_quality(),
        goal_id="goal-1",
    )
    context = AgentLoopContext(
        trace_id="trace-context",
        status=AgentLoopStatus.COMPLETED,
        decision_reference=reference,
    )
    assert context.decision_reference is not None
    assert context.decision_reference.risk_level == "LOW"
    assert context.decision_reference.recommended_options


def test_webui_decision_reference_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    builder = DecisionReferenceBuilder()
    reference = builder.build(
        environment_reference=_environment_reference(),
        planning_quality=_planning_quality(),
        goal_id="goal-1",
    )
    score = DecisionScorer().score(
        reference=reference,
        historical_success=0.6,
    )
    notes = DecisionRiskIntegrator().integrate(
        environment_reference=_environment_reference(),
    )
    payload = {
        "reference": reference.model_dump(mode="json"),
        "score": score.model_dump(mode="json"),
        "risk_notes": notes.risk_notes,
        "validation": {"valid": True, "issues": []},
    }
    app = create_app(runtime=runtime, bus=bus, decision_reference=payload)
    with TestClient(app) as client:
        resp = client.get("/api/decision-reference/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is True
    assert data["reference"]["risk_level"] == "LOW"
    assert data["reference"]["recommended_options"]
    assert data["score"]["decision_score"] == 0.83


def test_webui_decision_reference_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/decision-reference/state")
    assert resp.json()["enabled"] is False
