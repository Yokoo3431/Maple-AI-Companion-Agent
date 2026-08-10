"""Executor Sandbox 单测:token 验证 / 过期 / scope / 策略 / mock / replay / WebUI。"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from maple_agent.confirmation.models import PermissionToken
from maple_agent.events import EventBus
from maple_agent.executor_sandbox import (
    LimitedExecutorSandbox,
    SandboxExecutionRequest,
    SandboxExecutionStatus,
)
from maple_agent.runtime import RuntimeManager
from maple_agent.webui.app import create_app


def _token(
    *,
    approved: bool = True,
    scope: str = "TALK:赫丽娜",
    expires_in: int = 300,
) -> PermissionToken:
    return PermissionToken(
        token_id="tok-1",
        confirmation_id="conf-1",
        approved=approved,
        scope=scope,
        expires_at=datetime.now(UTC) + timedelta(seconds=expires_in),
    )


def _request(
    *,
    action: str = "TALK",
    target: str = "赫丽娜",
    scope: str = "TALK:赫丽娜",
) -> SandboxExecutionRequest:
    return SandboxExecutionRequest(
        execution_id="exec-1",
        trace_id="trace-sandbox",
        permission_token_id="tok-1",
        action=action,
        target=target,
        scope=scope,
    )


def test_valid_token_mock_execution():
    sandbox = LimitedExecutorSandbox()
    result = sandbox.execute(
        request=_request(),
        token=_token(),
    )
    assert result.status is SandboxExecutionStatus.COMPLETED
    assert result.success is True
    assert result.mode == "MOCK_ONLY"
    assert result.message == "mock sandbox execution only"
    assert result.audit["permission"] == "verified"
    assert result.audit["policy"] == "allowed"


def test_invalid_token_blocked():
    sandbox = LimitedExecutorSandbox()
    result = sandbox.execute(request=_request(), token=None)
    assert result.status is SandboxExecutionStatus.BLOCKED
    assert result.success is False
    assert result.mode == "MOCK_ONLY"
    assert result.audit["permission"] == "rejected"
    assert any("令牌不存在" in issue for issue in result.audit["validation"]["issues"])


def test_expired_token_blocked():
    sandbox = LimitedExecutorSandbox()
    result = sandbox.execute(
        request=_request(),
        token=_token(expires_in=-10),
    )
    assert result.status is SandboxExecutionStatus.BLOCKED
    issues = result.audit["validation"]["issues"]
    assert any("过期" in issue for issue in issues)


def test_unapproved_token_blocked():
    sandbox = LimitedExecutorSandbox()
    result = sandbox.execute(
        request=_request(),
        token=_token(approved=False),
    )
    assert result.status is SandboxExecutionStatus.BLOCKED
    issues = result.audit["validation"]["issues"]
    assert any("未批准" in issue for issue in issues)


def test_scope_mismatch_blocked():
    sandbox = LimitedExecutorSandbox()
    result = sandbox.execute(
        request=_request(scope="DEFEAT:绿水灵"),
        token=_token(),
    )
    assert result.status is SandboxExecutionStatus.BLOCKED
    issues = result.audit["validation"]["issues"]
    assert any("scope 不匹配" in issue for issue in issues)


def test_action_scope_mismatch_blocked():
    sandbox = LimitedExecutorSandbox()
    result = sandbox.execute(
        request=_request(action="DEFEAT", target="绿水灵"),
        token=_token(),
    )
    assert result.status is SandboxExecutionStatus.BLOCKED
    issues = result.audit["validation"]["issues"]
    assert any("action 与 scope 不匹配" in issue for issue in issues)


def test_blocked_action_policy():
    sandbox = LimitedExecutorSandbox()
    for action in ("DIRECT_INPUT", "RAW_CONTROL", "UNKNOWN", "DEFEAT"):
        result = sandbox.execute(
            request=_request(
                action=action,
                scope=f"{action}:x",
            ),
            token=_token(scope=f"{action}:x"),
        )
        assert result.status is SandboxExecutionStatus.BLOCKED
        issues = result.audit["validation"]["issues"]
        assert any("沙箱白名单" in issue or "禁止动作" in issue for issue in issues)


def test_mock_only_mode_always():
    sandbox = LimitedExecutorSandbox()
    ok = sandbox.execute(request=_request(), token=_token())
    blocked = sandbox.execute(request=_request(), token=None)
    assert ok.mode == "MOCK_ONLY"
    assert blocked.mode == "MOCK_ONLY"


def test_replay_generation(tmp_path):
    sandbox = LimitedExecutorSandbox(sessions_dir=tmp_path)
    sandbox.execute(
        request=_request(),
        token=_token(),
        trace_id="trace-replay",
    )
    replay = json.loads(
        (tmp_path / "trace-replay" / "sandbox_execution.json").read_text(
            encoding="utf-8"
        )
    )
    assert replay["execution_id"] == "exec-1"
    assert replay["action"] == "TALK"
    assert replay["target"] == "赫丽娜"
    assert replay["permission"] == "verified"
    assert replay["status"] == "COMPLETED"
    assert replay["mode"] == "MOCK_ONLY"
    assert replay["result"]["audit"]["scope"] == "TALK:赫丽娜"


def test_webui_executor_sandbox_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    sandbox = LimitedExecutorSandbox()
    result = sandbox.execute(
        request=_request(),
        token=_token(),
        trace_id="trace-webui",
    )
    payload = {
        "request": _request().model_dump(mode="json"),
        "result": result.model_dump(mode="json"),
    }
    app = create_app(runtime=runtime, bus=bus, executor_sandbox=payload)
    with TestClient(app) as client:
        resp = client.get("/api/executor-sandbox/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is True
    assert data["result"]["status"] == "COMPLETED"
    assert data["result"]["mode"] == "MOCK_ONLY"
    assert data["result"]["audit"]["permission"] == "verified"


def test_webui_executor_sandbox_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/executor-sandbox/state")
    assert resp.json()["enabled"] is False
