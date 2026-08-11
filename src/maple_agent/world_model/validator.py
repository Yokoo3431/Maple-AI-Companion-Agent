"""WorldModelValidator:历史与预测校验(只读)。"""

from __future__ import annotations

from pydantic import BaseModel, Field

from maple_agent.world_model.models import (
    EnvironmentHistory,
    PredictedEnvironmentState,
)


class WorldModelValidationResult(BaseModel):
    """世界模型校验结果。"""

    valid: bool
    issues: list[str] = Field(default_factory=list)


class WorldModelValidator:
    """检查历史非空 / 时间序列有序 / 预测置信度合理。"""

    def validate(
        self,
        *,
        history: EnvironmentHistory,
        prediction: PredictedEnvironmentState | None = None,
    ) -> WorldModelValidationResult:
        issues: list[str] = []
        if not history.snapshots:
            issues.append("历史为空")
        else:
            timestamps = [
                snapshot.timestamp for snapshot in history.snapshots
            ]
            if timestamps != sorted(timestamps):
                issues.append("快照时间序列无序")
        if prediction is not None and prediction.confidence > 0.9:
            issues.append("预测置信度过高(超保守上限)")
        return WorldModelValidationResult(
            valid=not issues,
            issues=issues,
        )
