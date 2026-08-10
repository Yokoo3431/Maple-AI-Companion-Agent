"""ActionPlanValidator:缺失 target / 未知 action / 不可满足前置 / 低置信。"""

from __future__ import annotations

from pydantic import BaseModel, Field

from maple_agent.action_plan.models import ActionPlan, ActionPlanStatus

# 与 decision.evaluator 白名单保持一致;本地定义避免 action_plan -> decision 依赖环
ALLOWED_ACTIONS = frozenset(
    {
        "OBSERVE",
        "ANALYZE",
        "QUERY_KNOWLEDGE",
        "WAIT",
        "PAUSE",
        "TALK",
        "COLLECT",
        "DEFEAT",
        "DELIVER",
        "COMPLETE",
        "MOVE_HINT",
    }
)


class ActionPlanValidationResult(BaseModel):
    """动作计划校验结果。"""

    valid: bool
    status: ActionPlanStatus
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class ActionPlanValidator:
    """校验动作计划;只返回结论,不触发任何执行。"""

    def __init__(self, *, min_confidence: float = 0.4) -> None:
        self.min_confidence = min_confidence

    def validate(self, plan: ActionPlan) -> ActionPlanValidationResult:
        errors: list[str] = []
        warnings: list[str] = []
        if not plan.action:
            errors.append("action 为空")
        elif plan.action not in ALLOWED_ACTIONS:
            errors.append(f"未知 action: {plan.action}")
        if not plan.target:
            errors.append("缺少 target")
        if plan.confidence < self.min_confidence:
            errors.append(
                f"置信度过低: {plan.confidence:.2f} < {self.min_confidence:.2f}"
            )
        impossible = [item for item in plan.prerequisites if item.startswith("缺失:")]
        if impossible:
            errors.append("前置条件不可满足: " + "、".join(impossible))
        if not plan.steps:
            warnings.append("无执行步骤")
        valid = not errors
        return ActionPlanValidationResult(
            valid=valid,
            status=ActionPlanStatus.READY if valid else ActionPlanStatus.BLOCKED,
            errors=errors,
            warnings=warnings,
        )
