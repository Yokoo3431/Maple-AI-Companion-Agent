"""Planner 契约模型(Phase 1.7,仅契约)。"""

from __future__ import annotations

from pydantic import BaseModel, Field

from maple_agent.context.models import AgentContext


class Goal(BaseModel):
    """目标。"""

    goal_id: str
    description: str
    priority: str = "NORMAL"
    deadline: str = ""


class Constraint(BaseModel):
    """约束。"""

    kind: str
    value: str = ""


class PlannerInput(BaseModel):
    """Planner 输入(序列化后的 AgentContext + 目标 + 约束)。"""

    context: AgentContext
    goals: list[Goal] = Field(default_factory=list)
    constraints: list[Constraint] = Field(default_factory=list)
    trace_id: str = ""


class PlanStep(BaseModel):
    """计划步骤。"""

    step_id: str
    action: str
    target: str = ""
    params: dict[str, str] = Field(default_factory=dict)
    depends_on: list[str] = Field(default_factory=list)
    expected_outcome: str = ""


class PlanResult(BaseModel):
    """计划结果。"""

    plan_id: str
    goal_id: str = ""
    steps: list[PlanStep] = Field(default_factory=list)
    summary: str = ""
    confidence: float = Field(default=0.0, ge=0, le=1)
    trace_id: str = ""
