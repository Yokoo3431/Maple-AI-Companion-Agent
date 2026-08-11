"""Environment-Aware Planning 单测:机会适配 / 风险约束 / 目标调整 / replay / context / WebUI。"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from maple_agent.agent_loop.models import AgentLoopContext, AgentLoopStatus
from maple_agent.environment_planning import (
    EnvironmentAwarePlanner,
    EnvironmentGoalAdapter,
    EnvironmentRiskAdapter,
    save_environment_planning_trace,
)
from maple_agent.environment_reasoning.models import (
    EnvironmentRiskReference,
    OpportunityReference,
    OpportunityType,
)
from maple_agent.events import EventBus
from maple_agent.runtime import RuntimeManager
from maple_agent.webui.app import create_app


def _opportunity(
    opportunity_type: OpportunityType,
    confidence: float = 0.9,
) -> OpportunityReference:
    return OpportunityReference(
        opportunity_type=opportunity_type,
        detail=opportunity_type.value,
        confidence=confidence,
    )


def _risk(level: str = "LOW") -> EnvironmentRiskReference:
    return EnvironmentRiskReference(
        risk_level=level,
        reason="环境稳定" if level == "LOW" else f"{level} 风险",
        recommendation="可正常推进",
    )


def test_goal_adapter_npc():
    adapter = EnvironmentGoalAdapter()
    adjustments = adapter.adapt(
        opportunities=[_opportunity(OpportunityType.NPC_INTERACTION)],
        goal_id="goal-1",
    )
    assert len(adjustments) == 1
    assert adjustments[0].suggested_priority == 85
    assert adjustments[0].goal_id == "goal-1"
    assert adjustments[0].opportunity_type == "NPC_INTERACTION"


def test_goal_adapter_all_types():
    adapter = EnvironmentGoalAdapter()
    opportunities = [
        _opportunity(OpportunityType.NPC_INTERACTION),
        _opportunity(OpportunityType.RESOURCE_AVAILABLE),
        _opportunity(OpportunityType.TASK_PROGRESS),
        _opportunity(OpportunityType.SAFE_AREA),
        _opportunity(OpportunityType.NEW_DISCOVERY),
    ]
    adjustments = adapter.adapt(opportunities=opportunities)
    assert len(adjustments) == 5
    assert adjustments[0].suggested_priority == 85
    assert adjustments[4].suggested_priority == 65


def test_risk_adapter_high():
    constraint = EnvironmentRiskAdapter().adapt(risk_reference=_risk("HIGH"))
    assert constraint.level == "blocked"
    assert "阻断" in constraint.recommendation


def test_risk_adapter_medium():
    constraint = EnvironmentRiskAdapter().adapt(
        risk_reference=_risk("MEDIUM"),
    )
    assert constraint.level == "warning"
    assert "谨慎" in constraint.recommendation


def test_risk_adapter_low():
    constraint = EnvironmentRiskAdapter().adapt(risk_reference=_risk("LOW"))
    assert constraint.level == "normal"
    assert constraint.recommendation == "可正常推进"


def test_goal_adjustment_build():
    planner = EnvironmentAwarePlanner()
    reference = planner.build_reference(
        opportunities=[
            _opportunity(OpportunityType.NPC_INTERACTION),
            _opportunity(OpportunityType.RESOURCE_AVAILABLE),
        ],
        risk_reference=_risk("LOW"),
        goal_id="goal-1",
    )
    assert reference.recommended_goals == ["goal-1"]
    assert reference.blocked_goals == []
    assert len(reference.priority_adjustments) == 2
    assert reference.opportunity_notes
    assert reference.confidence == 0.9


def test_high_risk_blocks_goal():
    planner = EnvironmentAwarePlanner()
    reference = planner.build_reference(
        opportunities=[_opportunity(OpportunityType.TASK_PROGRESS)],
        risk_reference=_risk("HIGH"),
        goal_id="goal-1",
    )
    assert reference.blocked_goals == ["goal-1"]
    assert reference.recommended_goals == []
    assert reference.risk_notes
    assert reference.confidence == 0.45


def test_replay_generation(tmp_path):
    planner = EnvironmentAwarePlanner()
    reference = planner.build_reference(
        opportunities=[_opportunity(OpportunityType.RESOURCE_AVAILABLE)],
        risk_reference=_risk("LOW"),
        goal_id="goal-1",
    )
    constraint = EnvironmentRiskAdapter().adapt(risk_reference=_risk("LOW"))
    save_environment_planning_trace(
        tmp_path,
        "trace-replay",
        environment_reference=reference,
        goal_adjustments=reference.priority_adjustments,
        risk_constraints=[constraint],
    )
    replay = json.loads(
        (
            tmp_path
            / "trace-replay"
            / "environment_planning_trace.json"
        ).read_text(encoding="utf-8")
    )
    assert replay["schema_version"] == "1.0"
    assert replay["environment_reference"]["recommended_goals"] == ["goal-1"]
    assert len(replay["goal_adjustments"]) == 1
    assert replay["risk_constraints"][0]["level"] == "normal"


def test_context_integration():
    planner = EnvironmentAwarePlanner()
    reference = planner.build_reference(
        opportunities=[_opportunity(OpportunityType.SAFE_AREA)],
        risk_reference=_risk("LOW"),
        goal_id="goal-1",
    )
    context = AgentLoopContext(
        trace_id="trace-context",
        status=AgentLoopStatus.COMPLETED,
        environment_planning_reference=reference,
    )
    assert context.environment_planning_reference is not None
    assert context.environment_planning_reference.recommended_goals == [
        "goal-1"
    ]
    assert context.environment_planning_reference.priority_adjustments


def test_webui_environment_planning_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    planner = EnvironmentAwarePlanner()
    reference = planner.build_reference(
        opportunities=[
            _opportunity(OpportunityType.NPC_INTERACTION),
            _opportunity(OpportunityType.RESOURCE_AVAILABLE),
        ],
        risk_reference=_risk("LOW"),
        goal_id="goal-1",
    )
    constraint = EnvironmentRiskAdapter().adapt(risk_reference=_risk("LOW"))
    payload = {
        "reference": reference.model_dump(mode="json"),
        "goal_adjustments": [
            adjustment.model_dump(mode="json")
            for adjustment in reference.priority_adjustments
        ],
        "risk_constraints": [constraint.model_dump(mode="json")],
        "validation": {"valid": True, "issues": []},
    }
    app = create_app(
        runtime=runtime,
        bus=bus,
        environment_planning=payload,
    )
    with TestClient(app) as client:
        resp = client.get("/api/environment-planning/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is True
    assert data["reference"]["recommended_goals"] == ["goal-1"]
    assert len(data["goal_adjustments"]) == 2
    assert data["risk_constraints"][0]["level"] == "normal"


def test_webui_environment_planning_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/environment-planning/state")
    assert resp.json()["enabled"] is False
