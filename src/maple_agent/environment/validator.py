"""EnvironmentValidator:环境状态校验(只读)。"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import StrEnum

from pydantic import BaseModel, Field

from maple_agent.environment.models import EnvironmentState


class EnvironmentVerdict(StrEnum):
    """环境校验结论。"""

    VALID = "VALID"
    WARNING = "WARNING"
    BLOCKED = "BLOCKED"


class EnvironmentValidationResult(BaseModel):
    """环境校验结果。"""

    verdict: EnvironmentVerdict
    issues: list[str] = Field(default_factory=list)


class EnvironmentValidator:
    """检查空环境 / 状态冲突 / 时间异常 / 数据一致性。"""

    def validate(
        self,
        state: EnvironmentState,
    ) -> EnvironmentValidationResult:
        issues: list[str] = []
        if not state.location and not state.visible_entities:
            issues.append("空环境: 无位置与实体")
        if state.conditions.get("conflict") is True:
            issues.append("状态冲突: conditions 标记冲突")
        if state.timestamp > datetime.now(UTC) + timedelta(minutes=5):
            issues.append("时间异常: timestamp 在未来")
        if state.confidence < 0.5 and state.visible_entities:
            issues.append("数据一致性: 低置信但有可见实体")
        if state.location and not state.world_context:
            issues.append("环境摘要缺失")
        blocked = any(
            "空环境" in issue
            or "状态冲突" in issue
            or "时间异常" in issue
            for issue in issues
        )
        verdict = (
            EnvironmentVerdict.BLOCKED
            if blocked
            else (
                EnvironmentVerdict.WARNING
                if issues
                else EnvironmentVerdict.VALID
            )
        )
        return EnvironmentValidationResult(
            verdict=verdict,
            issues=issues,
        )
