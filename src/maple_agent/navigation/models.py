"""Navigation Planning 数据模型(Phase 12-A,只读导航参考,不执行移动)。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class RouteStepType(StrEnum):
    """路由步骤类型。"""

    MAP_TRANSITION = "MAP_TRANSITION"
    PORTAL_REFERENCE = "PORTAL_REFERENCE"
    LOCAL_MOVE_REFERENCE = "LOCAL_MOVE_REFERENCE"
    NPC_REFERENCE = "NPC_REFERENCE"
    QUEST_TARGET_REFERENCE = "QUEST_TARGET_REFERENCE"


class RouteStep(BaseModel):
    """单步路由参考(不是移动命令)。"""

    step_type: RouteStepType
    source: str = ""
    target: str = ""
    metadata: dict = Field(default_factory=dict)


class NavigationReference(BaseModel):
    """导航参考(只规划,不执行)。"""

    navigation_id: str
    start_location: str = ""
    target_location: str = ""
    route_steps: list[RouteStep] = Field(default_factory=list)
    estimated_cost: float = Field(default=0.0, ge=0)
    confidence: float = Field(default=0.0, ge=0, le=1)
    reasoning: list[str] = Field(default_factory=list)
    validation: str = ""
