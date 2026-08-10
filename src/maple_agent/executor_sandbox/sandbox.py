"""LimitedExecutorSandbox:Token 验证 -> 策略验证 -> Mock 执行 -> Replay。"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from maple_agent.confirmation.models import PermissionToken
from maple_agent.executor_sandbox.models import (
    SandboxExecutionRequest,
    SandboxExecutionResult,
    SandboxExecutionStatus,
)
from maple_agent.executor_sandbox.policy import SandboxPolicy
from maple_agent.executor_sandbox.validator import SandboxValidator

logger = logging.getLogger("maple_agent.executor_sandbox")


class LimitedExecutorSandbox:
    """受限执行沙箱;禁止调用 Executor / Input Layer,仅 Mock。"""

    def __init__(
        self,
        *,
        policy: SandboxPolicy | None = None,
        validator: SandboxValidator | None = None,
        sessions_dir: str | Path = "sessions",
    ) -> None:
        self.policy = policy or SandboxPolicy()
        self.validator = validator or SandboxValidator(policy=self.policy)
        self.sessions_dir = Path(sessions_dir)
        self.last_result: SandboxExecutionResult | None = None

    def execute(
        self,
        *,
        request: SandboxExecutionRequest,
        token: PermissionToken | None,
        trace_id: str | None = None,
    ) -> SandboxExecutionResult:
        """接收请求 -> 验证 token/policy -> Mock 执行 -> 结果 + Replay。"""
        tid = trace_id or request.trace_id
        validation = self.validator.validate(request=request, token=token)
        if not validation.valid:
            result = SandboxExecutionResult(
                execution_id=request.execution_id,
                status=SandboxExecutionStatus.BLOCKED,
                success=False,
                message="; ".join(validation.issues),
                mode="MOCK_ONLY",
                audit={
                    "permission": "rejected",
                    "validation": validation.model_dump(mode="json"),
                },
            )
            self.last_result = result
            self._write_replay(request, result, tid)
            logger.info(
                "sandbox blocked: action=%s issues=%d",
                request.action,
                len(validation.issues),
            )
            return result
        result = SandboxExecutionResult(
            execution_id=request.execution_id,
            status=SandboxExecutionStatus.COMPLETED,
            success=True,
            message="mock sandbox execution only",
            mode="MOCK_ONLY",
            audit={
                "permission": "verified",
                "token_id": token.token_id if token is not None else "",
                "scope": token.scope if token is not None else "",
                "policy": "allowed",
            },
        )
        self.last_result = result
        self._write_replay(request, result, tid)
        logger.info(
            "sandbox executed: action=%s status=%s mode=%s",
            request.action,
            result.status.value,
            result.mode,
        )
        return result

    def _write_replay(
        self,
        request: SandboxExecutionRequest,
        result: SandboxExecutionResult,
        trace_id: str,
    ) -> None:
        if not trace_id:
            return
        directory = self.sessions_dir / trace_id
        directory.mkdir(parents=True, exist_ok=True)
        payload = {
            "execution_id": request.execution_id,
            "action": request.action,
            "target": request.target,
            "permission": result.audit.get("permission", "unknown"),
            "status": result.status.value,
            "mode": result.mode,
            "request": request.model_dump(mode="json"),
            "result": result.model_dump(mode="json"),
            "trace_id": trace_id,
        }
        (directory / "sandbox_execution.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
