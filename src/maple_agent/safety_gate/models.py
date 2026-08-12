"""Safety Gate 数据模型(Phase 13-A,动作安全审核参考,不执行)。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class SafetyDecisionType(StrEnum):
    """安全决策类型(不是执行许可)。"""

    ALLOW = "ALLOW"
    WARNING = "WARNING"
    BLOCKED = "BLOCKED"


class SafetyEvaluationReference(BaseModel):
    """安全审核参考(Reference,不是 Command)。"""

    evaluation_id: str
    source_action: str = ""
    decision: SafetyDecisionType = SafetyDecisionType.ALLOW
    risk_factors: list[str] = Field(default_factory=list)
    reasoning: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0, le=1)
    validation: str = ""
