"""SandboxValidator:Token 存在性 / 批准 / 过期 / scope / 策略检查。"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from maple_agent.confirmation.models import PermissionToken
from maple_agent.executor_sandbox.models import SandboxExecutionRequest
from maple_agent.executor_sandbox.policy import SandboxPolicy


class SandboxValidationStatus(StrEnum):
    """沙箱校验结论。"""

    VALID = "VALID"
    BLOCKED = "BLOCKED"


class SandboxValidationResult(BaseModel):
    """沙箱校验结果。"""

    valid: bool
    status: SandboxValidationStatus
    issues: list[str] = Field(default_factory=list)


class SandboxValidator:
    """校验 PermissionToken 与策略;只读判断。"""

    def __init__(self, *, policy: SandboxPolicy | None = None) -> None:
        self.policy = policy or SandboxPolicy()

    def validate(
        self,
        *,
        request: SandboxExecutionRequest,
        token: PermissionToken | None,
    ) -> SandboxValidationResult:
        issues: list[str] = []
        if token is None:
            issues.append("权限令牌不存在")
        else:
            if not token.approved:
                issues.append("权限令牌未批准")
            if token.expires_at < datetime.now(UTC):
                issues.append("权限令牌已过期")
            if request.scope and token.scope != request.scope:
                issues.append(
                    f"scope 不匹配: {token.scope} != {request.scope}"
                )
            token_action = token.scope.split(":", 1)[0].strip()
            if token_action and request.action != token_action:
                issues.append(
                    f"action 与 scope 不匹配: "
                    f"{request.action} != {token_action}"
                )
        if not self.policy.allows(request.action):
            issues.append(self.policy.block_reason(request.action))
        valid = not issues
        return SandboxValidationResult(
            valid=valid,
            status=(
                SandboxValidationStatus.VALID
                if valid
                else SandboxValidationStatus.BLOCKED
            ),
            issues=issues,
        )
