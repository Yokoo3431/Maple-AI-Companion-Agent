"""Failure Recovery 单测:失败检测/恢复映射/校验/replay/context/WebUI。"""

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
from maple_agent.recovery import (
    FailureDetector,
    FailureType,
    RecoveryPlanner,
    RecoveryReference,
    RecoveryType,
    RecoveryValidator,
    RecoveryVerdict,
    save_recovery_trace,
)
from maple_agent.runtime import RuntimeManager
from maple_agent.safety_gate.models import (
    SafetyDecisionType,
    SafetyEvaluationReference,
)
from maple_agent.webui.app import create_app


def _action(
    action_type: ActionType = ActionType.NAVIGATE,
    target: str = "赫丽娜",
) -> ActionProposalReference:
    return ActionProposalReference(
        action_id="action-1",
        action_type=action_type,
        target_reference=target,
        confidence=0.9,
    )


def _safety(
    decision: SafetyDecisionType = SafetyDecisionType.ALLOW,
) -> SafetyEvaluationReference:
    return SafetyEvaluationReference(
        evaluation_id="eval-1",
        source_action="NAVIGATE: 赫丽娜",
        decision=decision,
        confidence=0.9,
    )


def _game_state() -> GameStateReference:
    return GameStateReference(
        state_id="state-1",
        player_state=PlayerStateReference(hp=0.8, mp=0.6),
        current_map=MapStateReference(
            map_name="射手村",
            known_map=True,
        ),
        confidence=0.9,
    )


def _detect(action, **kwargs):
    return FailureDetector().detect(
        action,
        game_state=_game_state(),
        safety_evaluation=_safety(),
        **kwargs,
    )


def test_models_creation():
    assert FailureType.NAVIGATION_TIMEOUT.value == "NAVIGATION_TIMEOUT"
    assert RecoveryType.ABORT_REFERENCE.value == "ABORT_REFERENCE"
    reference = RecoveryReference(
        recovery_id="recovery-1",
        source_action="NAVIGATE: 赫丽娜",
        failure_type=FailureType.NAVIGATION_TIMEOUT,
        recovery_type=RecoveryType.RETRY_REFERENCE,
        confidence=0.8,
    )
    assert reference.failure_type is FailureType.NAVIGATION_TIMEOUT
    assert reference.recovery_type is RecoveryType.RETRY_REFERENCE


def test_detector_navigation_timeout():
    failure = _detect(_action(), timeout_hint=True)
    assert failure is FailureType.NAVIGATION_TIMEOUT


def test_detector_state_mismatch():
    failure = _detect(
        _action(action_type=ActionType.INTERACT),
        npc_missing=True,
    )
    assert failure is FailureType.STATE_MISMATCH


def test_detector_combat_failure():
    failure = _detect(
        _action(action_type=ActionType.COMBAT, target="绿水灵"),
        hp_decreased=True,
    )
    assert failure is FailureType.COMBAT_FAILURE


def test_detector_safety_blocked():
    failure = FailureDetector().detect(
        _action(),
        game_state=_game_state(),
        safety_evaluation=_safety(SafetyDecisionType.BLOCKED),
    )
    assert failure is FailureType.SAFETY_BLOCKED


def test_detector_unknown():
    failure = _detect(_action())
    assert failure is FailureType.UNKNOWN


def test_planner_mapping():
    planner = RecoveryPlanner()
    action = _action()
    cases = [
        (
            FailureType.NAVIGATION_TIMEOUT,
            RecoveryType.RETRY_REFERENCE,
        ),
        (FailureType.STATE_MISMATCH, RecoveryType.REPLAN_REFERENCE),
        (
            FailureType.COMBAT_FAILURE,
            RecoveryType.WAIT_OBSERVATION_REFERENCE,
        ),
        (FailureType.SAFETY_BLOCKED, RecoveryType.ABORT_REFERENCE),
    ]
    for failure, expected in cases:
        reference = planner.plan(action, failure)
        assert reference.recovery_type is expected


def test_planner_confidence():
    planner = RecoveryPlanner()
    timeout = planner.plan(
        _action(),
        FailureType.NAVIGATION_TIMEOUT,
    )
    abort = planner.plan(
        _action(),
        FailureType.SAFETY_BLOCKED,
    )
    assert timeout.confidence == 0.8
    assert abort.confidence == 0.95


def test_validator_valid():
    reference = RecoveryPlanner().plan(
        _action(),
        FailureType.NAVIGATION_TIMEOUT,
    )
    result = RecoveryValidator().validate(reference)
    assert result.verdict is RecoveryVerdict.VALID
    assert result.issues == []


def test_validator_warning_unknown():
    reference = RecoveryPlanner().plan(
        _action(),
        FailureType.UNKNOWN,
    )
    result = RecoveryValidator().validate(reference)
    assert result.verdict is RecoveryVerdict.WARNING
    assert any("unknown failure" in issue for issue in result.issues)


def test_validator_blocked():
    reference = RecoveryReference(
        recovery_id="",
        failure_type=FailureType.NAVIGATION_TIMEOUT,
        recovery_type=RecoveryType.RETRY_REFERENCE,
        confidence=0.8,
    )
    result = RecoveryValidator().validate(reference)
    assert result.verdict is RecoveryVerdict.BLOCKED
    assert "missing recovery id" in result.issues


def test_replay_generation(tmp_path):
    reference = RecoveryPlanner().plan(
        _action(),
        FailureType.NAVIGATION_TIMEOUT,
    )
    validation = RecoveryValidator().validate(reference)
    save_recovery_trace(
        tmp_path,
        "trace-replay",
        action=reference.source_action,
        failure=reference.failure_type.value,
        recovery=reference.recovery_type.value,
        validation=validation.verdict.value,
    )
    replay = json.loads(
        (tmp_path / "trace-replay" / "recovery_trace.json").read_text(
            encoding="utf-8"
        )
    )
    assert replay["schema_version"] == "1.0"
    assert replay["action"] == "NAVIGATE: 赫丽娜"
    assert replay["failure"] == "NAVIGATION_TIMEOUT"
    assert replay["recovery"] == "RETRY_REFERENCE"
    assert replay["validation"] == "VALID"


def test_agent_loop_integration():
    reference = RecoveryPlanner().plan(
        _action(),
        FailureType.NAVIGATION_TIMEOUT,
    )
    context = AgentLoopContext(
        trace_id="trace-recovery",
        status=AgentLoopStatus.REFLECTING,
        recovery_reference=reference,
    )
    assert context.recovery_reference is not None
    assert (
        context.recovery_reference.recovery_type
        is RecoveryType.RETRY_REFERENCE
    )


def test_webui_recovery_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    reference = RecoveryPlanner().plan(
        _action(),
        FailureType.NAVIGATION_TIMEOUT,
    )
    validation = RecoveryValidator().validate(reference)
    payload = {
        "source_action": reference.source_action,
        "failure_type": reference.failure_type.value,
        "recovery_type": reference.recovery_type.value,
        "reasoning": reference.reasoning,
        "confidence": reference.confidence,
        "validation": validation.verdict.value,
    }
    app = create_app(runtime=runtime, bus=bus, recovery=payload)
    with TestClient(app) as client:
        resp = client.get("/api/recovery/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is True
    assert data["source_action"] == "NAVIGATE: 赫丽娜"
    assert data["failure_type"] == "NAVIGATION_TIMEOUT"
    assert data["recovery_type"] == "RETRY_REFERENCE"
    assert data["validation"] == "VALID"


def test_webui_recovery_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/recovery/state")
    assert resp.json()["enabled"] is False
