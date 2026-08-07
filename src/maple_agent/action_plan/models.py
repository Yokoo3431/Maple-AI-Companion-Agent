"""Action Plan 领域模型(Phase 5-B,仅可执行规格契约,不执行动作)。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ActionPlanStatus(StrEnum):
    """动作计划状态。"""

    DRAFT = "DRAFT"
    VALIDATING = "VALIDATING"
    READY = "READY"
    BLOCKED = "BLOCKED"


class ActionStep(BaseModel):
    """动作计划的步骤规格(语义描述,非物理指令)。"""

    step_id: str
    description: str
    required_observation: str = ""
    success_condition: str = ""


class ActionPlan(BaseModel):
    """动作计划(DecisionOption 展开后的可执行规格契约)。"""

    plan_id: str
    decision_id: str = ""
    goal_id: str = ""
    action: str
    target: str = ""
    prerequisites: list[str] = Field(default_factory=list)
    validation_conditions: list[str] = Field(default_factory=list)
    expected_result: str = ""
    confidence: float = Field(default=0.0, ge=0, le=1)
    status: ActionPlanStatus = ActionPlanStatus.DRAFT
    steps: list[ActionStep] = Field(default_factory=list)
    trace_id: str = ""
