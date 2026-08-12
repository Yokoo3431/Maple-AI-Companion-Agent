"""Safety Gate 单测:ALLOW/WARNING/BLOCKED/风险规则/校验/replay/context/WebUI。"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from maple_agent.action_proposal.models import (
    ActionProposalReference,
    ActionType,
)
from maple_agent.agent_loop.models import AgentLoopContext, AgentLoopStatus
from maple_agent.events import EventBus
from maple_agent.game_state.models import (
    GameStateReference,
    MapStateReference,
    PlayerStateReference,
)
from maple_agent.reflex.models import ReflexReference, ReflexStateType
from maple_agent.runtime import RuntimeManager
from maple_agent.safety_gate import (
    SafetyDecisionType,
    SafetyEvaluationReference,
    SafetyEvaluator,
    SafetyGateValidator,
    SafetyGateVerdict,
    save_safety_gate_trace,
)
from maple_agent.webui.app import create_app


def _action(
    action_type: ActionType = ActionType.INTERACT,
    target: str = "赫丽娜",
) -> ActionProposalReference:
    return ActionProposalReference(
        action_id="action-1",
        action_type=action_type,
        target_reference=target,
        confidence=0.9,
    )


def _game_state(hp: float = 0.8) -> GameStateReference:
    return GameStateReference(
        state_id="state-1",
        player_state=PlayerStateReference(hp=hp, mp=0.6),
        current_map=MapStateReference(
            map_name="射手村",
            known_map=True,
        ),
        confidence=0.9,
    )


def _reflex(state: ReflexStateType = ReflexStateType.NORMAL) -> ReflexReference:
    return ReflexReference(
        reflex_id="reflex-1",
        state=state,
        confidence=0.9,
    )


def _evaluate(action, *, hp: float = 0.8, reflex: ReflexStateType = ReflexStateType.NORMAL):
    return SafetyEvaluator().evaluate(
        action,
        game_state_reference=_game_state(hp),
        reflex_reference=_reflex(reflex),
    )


def test_decision_enum():
    assert SafetyDecisionType.ALLOW.value == "ALLOW"
    assert SafetyDecisionType.WARNING.value == "WARNING"
    assert SafetyDecisionType.BLOCKED.value == "BLOCKED"


def test_evaluation_creation():
    reference = SafetyEvaluationReference(
        evaluation_id="eval-1",
        source_action="INTERACT: 赫丽娜",
        decision=SafetyDecisionType.ALLOW,
        confidence=0.95,
    )
    assert reference.decision is SafetyDecisionType.ALLOW
    assert reference.risk_factors == []


def test_allow():
    evaluation = _evaluate(_action())
    assert evaluation.decision is SafetyDecisionType.ALLOW
    assert evaluation.risk_factors == []
    assert evaluation.confidence == 0.95


def test_warning_hp_risk():
    evaluation = _evaluate(
        _action(action_type=ActionType.COMBAT, target="绿水灵"),
        hp=0.2,
    )
    assert evaluation.decision is SafetyDecisionType.WARNING
    assert "hp low combat risk" in evaluation.risk_factors
    assert evaluation.confidence == 0.8


def test_blocked_death_risk():
    evaluation = _evaluate(_action(), reflex=ReflexStateType.DEATH)
    assert evaluation.decision is SafetyDecisionType.BLOCKED
    assert "death risk" in evaluation.risk_factors
    assert evaluation.confidence == 0.9


def test_warning_unknown_target():
    evaluation = _evaluate(_action(target=""))
    assert evaluation.decision is SafetyDecisionType.WARNING
    assert "unknown target" in evaluation.risk_factors


def test_blocked_invalid_action():
    invalid = ActionProposalReference.model_construct(
        action_id="action-bad",
        action_type="NOT_A_TYPE",
        target_reference="x",
        confidence=0.9,
    )
    evaluation = SafetyEvaluator().evaluate(
        invalid,
        game_state_reference=_game_state(),
        reflex_reference=_reflex(),
    )
    assert evaluation.decision is SafetyDecisionType.BLOCKED
    assert "invalid action" in evaluation.risk_factors


def test_validator_valid():
    evaluation = _evaluate(_action())
    result = SafetyGateValidator().validate(evaluation)
    assert result.verdict is SafetyGateVerdict.VALID
    assert result.issues == []


def test_validator_warning_missing_source():
    evaluation = SafetyEvaluationReference(
        evaluation_id="eval-warn",
        decision=SafetyDecisionType.ALLOW,
        confidence=0.95,
    )
    result = SafetyGateValidator().validate(evaluation)
    assert result.verdict is SafetyGateVerdict.WARNING
    assert any("missing source action" in issue for issue in result.issues)


def test_validator_blocked():
    reference = SafetyEvaluationReference(
        evaluation_id="",
        decision=SafetyDecisionType.ALLOW,
        confidence=0.95,
    )
    result = SafetyGateValidator().validate(reference)
    assert result.verdict is SafetyGateVerdict.BLOCKED
    assert "missing evaluation id" in result.issues


def test_replay_generation(tmp_path):
    evaluation = _evaluate(_action())
    validation = SafetyGateValidator().validate(evaluation)
    save_safety_gate_trace(
        tmp_path,
        "trace-replay",
        action=evaluation.source_action,
        decision=evaluation.decision.value,
        risk_factors=evaluation.risk_factors,
        validation=validation.verdict.value,
    )
    replay = json.loads(
        (tmp_path / "trace-replay" / "safety_gate_trace.json").read_text(
            encoding="utf-8"
        )
    )
    assert replay["schema_version"] == "1.0"
    assert replay["action"] == "INTERACT: 赫丽娜"
    assert replay["decision"] == "ALLOW"
    assert replay["risk_factors"] == []
    assert replay["validation"] == "VALID"


def test_agent_loop_integration():
    evaluation = _evaluate(_action())
    context = AgentLoopContext(
        trace_id="trace-safety",
        status=AgentLoopStatus.PLANNING,
        safety_evaluation_reference=evaluation,
    )
    assert context.safety_evaluation_reference is not None
    assert (
        context.safety_evaluation_reference.decision
        is SafetyDecisionType.ALLOW
    )


def test_webui_safety_gate_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    evaluation = _evaluate(_action())
    validation = SafetyGateValidator().validate(evaluation)
    payload = {
        "source_action": evaluation.source_action,
        "decision": evaluation.decision.value,
        "risk_factors": evaluation.risk_factors,
        "reasoning": evaluation.reasoning,
        "confidence": evaluation.confidence,
        "validation": validation.verdict.value,
    }
    app = create_app(runtime=runtime, bus=bus, safety_gate=payload)
    with TestClient(app) as client:
        resp = client.get("/api/safety-gate/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is True
    assert data["source_action"] == "INTERACT: 赫丽娜"
    assert data["decision"] == "ALLOW"
    assert data["risk_factors"] == []
    assert data["validation"] == "VALID"


def test_webui_safety_gate_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/safety-gate/state")
    assert resp.json()["enabled"] is False
