"""Environment Reasoning 数据模型(Phase 8-C,语义环境推理,只读)。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class OpportunityType(StrEnum):
    """环境机会类型。"""

    NPC_INTERACTION = "NPC_INTERACTION"
    RESOURCE_AVAILABLE = "RESOURCE_AVAILABLE"
    TASK_PROGRESS = "TASK_PROGRESS"
    SAFE_AREA = "SAFE_AREA"
    NEW_DISCOVERY = "NEW_DISCOVERY"


class EnvironmentInterpretation(BaseModel):
    """环境语义解释。"""

    meaning: str = ""
    possible_causes: list[str] = Field(default_factory=list)
    semantic_confidence: float = Field(default=0.0, ge=0, le=1)


class OpportunityReference(BaseModel):
    """环境机会参考。"""

    opportunity_type: OpportunityType
    detail: str = ""
    confidence: float = Field(default=0.0, ge=0, le=1)
    related_entities: list[str] = Field(default_factory=list)


class EnvironmentRiskReference(BaseModel):
    """环境风险评估参考。"""

    risk_level: str = ""
    reason: str = ""
    affected_goals: list[str] = Field(default_factory=list)
    recommendation: str = ""
