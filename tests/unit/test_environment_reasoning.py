"""Environment Reasoning 单测:语义 / 机会 / 风险 / replay / context / WebUI。"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from maple_agent.agent_loop.models import AgentLoopContext, AgentLoopStatus
from maple_agent.context.models import KnowledgeState, MatchedEntity
from maple_agent.environment.models import EnvironmentState
from maple_agent.environment_reasoning import (
    EnvironmentOpportunityDetector,
    EnvironmentReasoner,
    EnvironmentReasoningValidator,
    EnvironmentRiskAnalyzer,
    OpportunityType,
    save_environment_reasoning_trace,
)
from maple_agent.events import EventBus
from maple_agent.runtime import RuntimeManager
from maple_agent.webui.app import create_app
from maple_agent.world_model import (
    EnvironmentEvent,
    EnvironmentHistoryManager,
    WorldEventType,
)


def _state(
    *,
    location: str = "射手村",
    entities: list[str] | None = None,
    resources: list[str] | None = None,
    confidence: float = 0.95,
    conditions: dict | None = None,
) -> EnvironmentState:
    return EnvironmentState(
        environment_id="env-1",
        location=location,
        visible_entities=entities or ["赫丽娜"],
        resources=resources or [],
        conditions=conditions or {},
        world_context=f"当前位于 {location}",
        confidence=confidence,
    )


def _knowledge_state(
    entity_types: list[tuple[str, str]] | None = None,
) -> KnowledgeState:
    entities = [
        MatchedEntity(
            entity_type=entity_type,
            entity_id=index,
            name=name,
            confidence=0.9,
        )
        for index, (entity_type, name) in enumerate(
            entity_types or [("npc", "赫丽娜")]
        )
    ]
    return KnowledgeState(
        matched_entities=entities,
        confidence=0.9,
        source="test",
    )


def _history(locations: list[str] | None = None) -> EnvironmentHistoryManager:
    manager = EnvironmentHistoryManager()
    for index, location in enumerate(locations or ["射手村"]):
        manager.append(
            EnvironmentState(
                environment_id=f"env-{index}",
                location=location,
                visible_entities=["赫丽娜"],
                confidence=0.9,
            )
        )
    return manager


def test_semantic_reasoning():
    reasoner = EnvironmentReasoner()
    history = _history(["射手村", "魔法密林"]).history
    event = EnvironmentEvent(
        event_type=WorldEventType.LOCATION_CHANGED,
        detail="射手村 -> 魔法密林",
    )
    interpretation = reasoner.interpret(
        environment_state=_state(
            location="魔法密林",
            entities=["爱丽丝"],
            resources=["树液"],
        ),
        environment_history=history,
        world_events=[event],
    )
    assert "魔法密林" in interpretation.meaning
    assert "树液" in interpretation.meaning
    assert interpretation.possible_causes
    assert interpretation.semantic_confidence > 0.9


def test_opportunity_npc_interaction():
    detector = EnvironmentOpportunityDetector()
    opportunities = detector.detect(
        environment_state=_state(),
        knowledge_state=_knowledge_state([("npc", "赫丽娜")]),
    )
    assert any(
        opportunity.opportunity_type is OpportunityType.NPC_INTERACTION
        for opportunity in opportunities
    )


def test_opportunity_resources():
    detector = EnvironmentOpportunityDetector()
    opportunities = detector.detect(
        environment_state=_state(resources=["树液"]),
    )
    assert any(
        opportunity.opportunity_type
        is OpportunityType.RESOURCE_AVAILABLE
        for opportunity in opportunities
    )


def test_opportunity_safe_area_and_progress():
    detector = EnvironmentOpportunityDetector()
    opportunities = detector.detect(
        environment_state=_state(),
        knowledge_state=_knowledge_state([("npc", "赫丽娜")]),
    )
    types = {opportunity.opportunity_type for opportunity in opportunities}
    assert OpportunityType.SAFE_AREA in types
    assert OpportunityType.TASK_PROGRESS in types


def test_opportunity_new_discovery():
    detector = EnvironmentOpportunityDetector()
    opportunities = detector.detect(
        environment_state=_state(location="魔法密林"),
        history=_history(["射手村"]).history,
    )
    assert any(
        opportunity.opportunity_type is OpportunityType.NEW_DISCOVERY
        for opportunity in opportunities
    )


def test_risk_low():
    risk = EnvironmentRiskAnalyzer().analyze(
        environment_state=_state(),
    )
    assert risk.risk_level == "LOW"
    assert risk.recommendation == "可正常推进"


def test_risk_medium():
    risk = EnvironmentRiskAnalyzer().analyze(
        environment_state=_state(confidence=0.6),
    )
    assert risk.risk_level == "MEDIUM"
    assert "加强观察" in risk.recommendation


def test_risk_high():
    risk = EnvironmentRiskAnalyzer().analyze(
        environment_state=_state(confidence=0.3),
    )
    assert risk.risk_level == "HIGH"
    assert "重新观察" in risk.recommendation


def test_risk_high_location():
    risk = EnvironmentRiskAnalyzer().analyze(
        environment_state=_state(location="危险区域"),
    )
    assert risk.risk_level == "HIGH"


def test_replay_generation(tmp_path):
    reasoner = EnvironmentReasoner()
    detector = EnvironmentOpportunityDetector()
    state = _state(resources=["树液"])
    interpretation = reasoner.interpret(environment_state=state)
    opportunities = detector.detect(environment_state=state)
    risk = EnvironmentRiskAnalyzer().analyze(environment_state=state)
    save_environment_reasoning_trace(
        tmp_path,
        "trace-replay",
        interpretation=interpretation,
        opportunities=opportunities,
        risks=[risk],
    )
    replay = json.loads(
        (
            tmp_path
            / "trace-replay"
            / "environment_reasoning_trace.json"
        ).read_text(encoding="utf-8")
    )
    assert replay["schema_version"] == "1.0"
    assert "射手村" in replay["interpretation"]["meaning"]
    assert replay["opportunities"]
    assert replay["risks"][0]["risk_level"] == "LOW"


def test_validator_consistent():
    state = _state(confidence=0.3)
    interpretation = EnvironmentReasoner().interpret(
        environment_state=state,
    )
    opportunities = EnvironmentOpportunityDetector().detect(
        environment_state=state,
    )
    risk = EnvironmentRiskAnalyzer().analyze(environment_state=state)
    result = EnvironmentReasoningValidator().validate(
        interpretation=interpretation,
        opportunities=opportunities,
        risk_reference=risk,
    )
    # 低置信不产生 SAFE_AREA/TASK_PROGRESS,validator 应通过
    assert result.valid is True


def test_context_integration():
    state = _state()
    interpretation = EnvironmentReasoner().interpret(
        environment_state=state,
    )
    opportunities = EnvironmentOpportunityDetector().detect(
        environment_state=state,
    )
    risk = EnvironmentRiskAnalyzer().analyze(environment_state=state)
    context = AgentLoopContext(
        trace_id="trace-context",
        status=AgentLoopStatus.COMPLETED,
        environment_interpretation=interpretation,
        environment_opportunities=opportunities,
        environment_risk_reference=risk,
    )
    assert context.environment_interpretation is not None
    assert context.environment_interpretation.meaning
    assert context.environment_opportunities
    assert context.environment_risk_reference is not None
    assert context.environment_risk_reference.risk_level == "LOW"


def test_webui_environment_reasoning_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    state = _state(resources=["树液"])
    interpretation = EnvironmentReasoner().interpret(
        environment_state=state,
    )
    opportunities = EnvironmentOpportunityDetector().detect(
        environment_state=state,
    )
    risk = EnvironmentRiskAnalyzer().analyze(environment_state=state)
    validation = EnvironmentReasoningValidator().validate(
        interpretation=interpretation,
        opportunities=opportunities,
        risk_reference=risk,
    )
    payload = {
        "interpretation": interpretation.model_dump(mode="json"),
        "opportunities": [
            opportunity.model_dump(mode="json")
            for opportunity in opportunities
        ],
        "risk": risk.model_dump(mode="json"),
        "validation": validation.model_dump(mode="json"),
    }
    app = create_app(
        runtime=runtime,
        bus=bus,
        environment_reasoning=payload,
    )
    with TestClient(app) as client:
        resp = client.get("/api/environment-reasoning/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is True
    assert data["interpretation"]["meaning"]
    assert data["opportunities"]
    assert data["risk"]["risk_level"] == "LOW"


def test_webui_environment_reasoning_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/environment-reasoning/state")
    assert resp.json()["enabled"] is False
