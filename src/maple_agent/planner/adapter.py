"""AgentContext → PlannerInput 适配。"""

from __future__ import annotations

from maple_agent.context.models import AgentContext
from maple_agent.planner.models import Constraint, Goal, PlannerInput


def serialize_for_planner(
    context: AgentContext,
    *,
    goals: list[Goal] | None = None,
    constraints: list[Constraint] | None = None,
) -> PlannerInput:
    """把 AgentContext 转换为 PlannerInput,附默认安全约束。"""
    return PlannerInput(
        context=context,
        goals=goals or [],
        constraints=constraints
        or [
            Constraint(kind="safety", value="禁止自动输入 / 控制 / 任务执行"),
            Constraint(kind="execution", value="仅只读观察,不触发输入"),
        ],
        trace_id=context.trace_id,
    )
