"""ConfirmationValidator:请求存在性 / 过期 / 视觉评分 / 动作匹配检查。"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from maple_agent.confirmation.models import (
    ConfirmationRequest,
    ConfirmationStatus,
    PermissionToken,
)


class ConfirmationValidationResult(BaseModel):
    """确认校验结果。"""

    valid: bool
    status: ConfirmationStatus
    issues: list[str] = Field(default_factory=list)


class ConfirmationValidator:
    """校验人工授权是否可用于动作;只读判断。"""

    def __init__(self, *, min_vision_score: float = 0.5) -> None:
        self.min_vision_score = min_vision_score

    def validate(
        self,
        *,
        request: ConfirmationRequest | None,
        token: PermissionToken | None = None,
        action: str = "",
    ) -> ConfirmationValidationResult:
        issues: list[str] = []
        if request is None:
            return ConfirmationValidationResult(
                valid=False,
                status=ConfirmationStatus.BLOCKED,
                issues=["确认请求不存在"],
            )
        if request.status is not ConfirmationStatus.APPROVED:
            issues.append(f"确认状态非 APPROVED: {request.status.value}")
        if token is None:
            issues.append("缺少权限令牌")
        else:
            if not token.approved:
                issues.append("权限令牌未批准")
            if token.expires_at < datetime.now(UTC):
                issues.append("权限令牌已过期")
        if request.vision_score < self.min_vision_score:
            issues.append(
                f"视觉评分 {request.vision_score:.2f} 低于阈值 "
                f"{self.min_vision_score:.2f}"
            )
        if action and request.action != action:
            issues.append(f"动作不匹配: {request.action} != {action}")
        valid = not issues
        return ConfirmationValidationResult(
            valid=valid,
            status=(
                ConfirmationStatus.APPROVED
                if valid
                else ConfirmationStatus.BLOCKED
            ),
            issues=issues,
        )
