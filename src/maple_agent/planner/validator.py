"""PlanValidator:动作合法性与约束冲突检查。"""

from __future__ import annotations

from maple_agent.planner.action import ALLOWED_ACTIONS
from maple_agent.planner.models import Constraint, PlanResult


class PlanValidationError(ValueError):
    """计划校验失败。"""


class PlanValidator:
    """校验 PlanResult 的动作是否合法、是否与约束冲突。"""

    def validate(
        self,
        result: PlanResult,
        constraints: list[Constraint] | None = None,
    ) -> None:
        if not result.steps:
            raise PlanValidationError("计划为空(无步骤)")
        for step in result.steps:
            action = (step.action or "").strip().lower()
            if action not in ALLOWED_ACTIONS:
                raise PlanValidationError(
                    f"非法动作: {step.action!r};允许: {sorted(ALLOWED_ACTIONS)}"
                )
        for constraint in constraints or []:
            if constraint.kind != "forbidden_actions":
                continue
            forbidden = {
                item.strip().lower()
                for item in constraint.value.split(",")
                if item.strip()
            }
            for step in result.steps:
                if (step.action or "").strip().lower() in forbidden:
                    raise PlanValidationError(
                        f"动作 {step.action!r} 与约束冲突: {constraint.value!r}"
                    )
