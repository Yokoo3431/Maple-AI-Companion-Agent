"""Human Confirmation 单测:创建 / 批准 / 拒绝 / 过期 / 阻断 / token / replay / WebUI。"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from maple_agent.action_plan.models import ActionPlan, ActionPlanStatus, ActionStep
from maple_agent.confirmation import (
    ConfirmationError,
    ConfirmationManager,
    ConfirmationRequest,
    ConfirmationStatus,
    ConfirmationValidator,
    HumanConfirmationGate,
)
from maple_agent.decision.models import DecisionOption, DecisionResult
from maple_agent.events import EventBus
from maple_agent.runtime import RuntimeManager
from maple_agent.vision_eval.models import RiskLevel, VisionEvaluationResult
from maple_agent.webui.app import create_app


def _action_plan() -> ActionPlan:
    return ActionPlan(
        plan_id="plan-1",
        decision_id="d1",
        goal_id="goal-1",
        action="TALK",
        target="赫丽娜",
        confidence=0.9,
        status=ActionPlanStatus.READY,
        steps=[
            ActionStep(
                step_id="step-1",
                description="与 NPC 对话",
            )
        ],
    )


def _vision_result(
    risk: RiskLevel = RiskLevel.LOW,
    score: float = 0.9,
) -> VisionEvaluationResult:
    return VisionEvaluationResult(
        evaluation_id="e1",
        frame_id="f1",
        overall_score=score,
        ocr_score=0.9,
        entity_score=0.8,
        consistency_score=1.0,
        confidence_score=1.0,
        risk_level=risk,
    )


def _decision(confidence: float = 0.9) -> DecisionResult:
    return DecisionResult(
        selected_option=DecisionOption(
            decision_id="d1",
            action="TALK",
            target="赫丽娜",
            confidence=confidence,
            risk=0.2,
        ),
        alternatives=[],
        score=0.8,
    )


def _create_request(
    manager: ConfirmationManager,
    *,
    risk: RiskLevel = RiskLevel.LOW,
    confidence: float = 0.9,
    trace_id: str = "trace-confirm",
) -> ConfirmationRequest:
    request = HumanConfirmationGate().create_request(
        action_plan=_action_plan(),
        vision_result=_vision_result(risk=risk),
        decision_result=_decision(confidence=confidence),
        trace_id=trace_id,
    )
    manager.create(request)
    return request


def test_request_creation():
    manager = ConfirmationManager()
    request = _create_request(manager)
    assert request.status is ConfirmationStatus.PENDING
    assert request.action == "TALK"
    assert request.target == "赫丽娜"
    assert request.action_plan_id == "plan-1"
    assert request.vision_score == 0.9
    assert request.risk_level == "LOW"
    assert request.reason == "等待人工确认"


def test_approve_issues_token():
    manager = ConfirmationManager()
    request = _create_request(manager)
    token = manager.approve(request.confirmation_id)
    assert token.approved is True
    assert token.confirmation_id == request.confirmation_id
    assert token.scope == "TALK:赫丽娜"
    assert token.expires_at > datetime.now(UTC)
    assert request.status is ConfirmationStatus.APPROVED
    assert manager.last_token is token


def test_reject():
    manager = ConfirmationManager()
    request = _create_request(manager)
    manager.reject(request.confirmation_id)
    assert request.status is ConfirmationStatus.REJECTED


def test_expire():
    manager = ConfirmationManager()
    request = _create_request(manager)
    manager.expire(request.confirmation_id)
    assert request.status is ConfirmationStatus.EXPIRED


def test_approve_non_pending_raises():
    manager = ConfirmationManager()
    request = _create_request(manager)
    manager.reject(request.confirmation_id)
    with pytest.raises(ConfirmationError):
        manager.approve(request.confirmation_id)


def test_high_risk_blocked():
    manager = ConfirmationManager()
    request = _create_request(manager, risk=RiskLevel.HIGH)
    assert request.status is ConfirmationStatus.BLOCKED
    assert "HIGH" in request.reason
    with pytest.raises(ConfirmationError):
        manager.approve(request.confirmation_id)


def test_low_confidence_pending():
    manager = ConfirmationManager()
    request = _create_request(manager, confidence=0.3)
    assert request.status is ConfirmationStatus.PENDING
    assert "低于阈值" in request.reason


def test_permission_token_fields():
    manager = ConfirmationManager()
    request = _create_request(manager)
    token = manager.approve(request.confirmation_id)
    assert token.token_id
    assert token.approved is True
    assert token.scope == "TALK:赫丽娜"


def test_replay_generation(tmp_path):
    manager = ConfirmationManager(sessions_dir=tmp_path)
    request = _create_request(manager, trace_id="trace-replay")
    manager.approve(request.confirmation_id)
    replay = json.loads(
        (tmp_path / "trace-replay" / "confirmation_trace.json").read_text(
            encoding="utf-8"
        )
    )
    assert replay["confirmation_id"] == request.confirmation_id
    assert replay["action"] == "TALK"
    assert replay["target"] == "赫丽娜"
    assert replay["vision_score"] == 0.9
    assert replay["risk"] == "LOW"
    assert replay["status"] == "APPROVED"
    assert replay["permission"] == "issued"
    assert replay["token"]["approved"] is True


def test_validator_valid():
    manager = ConfirmationManager()
    request = _create_request(manager)
    token = manager.approve(request.confirmation_id)
    result = ConfirmationValidator().validate(
        request=request,
        token=token,
        action="TALK",
    )
    assert result.valid is True
    assert result.status is ConfirmationStatus.APPROVED


def test_validator_expired_token():
    manager = ConfirmationManager()
    request = _create_request(manager)
    token = manager.approve(request.confirmation_id)
    token.expires_at = datetime.now(UTC) - timedelta(seconds=10)
    result = ConfirmationValidator().validate(
        request=request,
        token=token,
        action="TALK",
    )
    assert result.valid is False
    assert any("过期" in issue for issue in result.issues)


def test_validator_action_mismatch():
    manager = ConfirmationManager()
    request = _create_request(manager)
    token = manager.approve(request.confirmation_id)
    result = ConfirmationValidator().validate(
        request=request,
        token=token,
        action="DEFEAT",
    )
    assert result.valid is False
    assert any("动作不匹配" in issue for issue in result.issues)


def test_validator_missing_request():
    result = ConfirmationValidator().validate(request=None)
    assert result.valid is False
    assert result.status is ConfirmationStatus.BLOCKED


def test_webui_confirmation_endpoint_and_actions():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    manager = ConfirmationManager(sessions_dir="sessions")
    request = _create_request(manager, trace_id="trace-webui")
    payload = {"request": request.model_dump(mode="json"), "token": None}
    app = create_app(
        runtime=runtime,
        bus=bus,
        confirmation_manager=manager,
        confirmation=payload,
    )
    with TestClient(app) as client:
        resp = client.get("/api/confirmation/state")
        data = resp.json()
        assert resp.status_code == 200
        assert data["enabled"] is True
        assert data["request"]["status"] == "PENDING"
        approve = client.post(
            "/api/confirmation/approve",
            json={"confirmation_id": request.confirmation_id},
        )
        assert approve.status_code == 200
        assert approve.json()["token"]["approved"] is True
        reject = client.post(
            "/api/confirmation/reject",
            json={"confirmation_id": "missing-id"},
        )
        assert reject.status_code == 409
        assert reject.json()["ok"] is False


def test_webui_confirmation_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/confirmation/state")
    assert resp.json()["enabled"] is False
