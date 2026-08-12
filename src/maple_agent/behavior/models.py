"""Behavior Planning 数据模型(Phase 12-B,高层行为参考,不执行)。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class BehaviorStepType(StrEnum):
    """语义行为类型(不是执行命令)。"""

    QUEST_ANALYSIS = "QUEST_ANALYSIS"
    NAVIGATE_REFERENCE = "NAVIGATE_REFERENCE"
    INTERACT_REFERENCE = "INTERACT_REFERENCE"
    COMBAT_REFERENCE = "COMBAT_REFERENCE"
    COLLECT_REFERENCE = "COLLECT_REFERENCE"
    VERIFY_REFERENCE = "VERIFY_REFERENCE"
    WAIT_REFERENCE = "WAIT_REFERENCE"


class BehaviorStep(BaseModel):
    """单步语义行为(Reference,不是 Action)。"""

    step_type: BehaviorStepType
    description: str = ""
    target: str = ""
    metadata: dict = Field(default_factory=dict)


class BehaviorReference(BaseModel):
    """行为规划参考(只规划,不执行)。"""

    behavior_id: str
    goal_reference: str = ""
    behavior_steps: list[BehaviorStep] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0, le=1)
    reasoning: list[str] = Field(default_factory=list)
    validation: str = ""
