"""Decision Reference 数据模型(Phase 8-E,决策参考层,只读)。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ReferenceOption(BaseModel):
    """决策参考选项(非 Action)。"""

    option_id: str
    action: str = ""
    target: str = ""
    recommendation: str = ""
    confidence: float = Field(default=0.0, ge=0, le=1)
    reason: str = ""


class DecisionReference(BaseModel):
    """决策参考(推荐/备选/风险/对齐度)。"""

    recommended_options: list[ReferenceOption] = Field(
        default_factory=list
    )
    alternative_options: list[ReferenceOption] = Field(
        default_factory=list
    )
    risk_level: str = ""
    confidence: float = Field(default=0.0, ge=0, le=1)
    reasoning: list[str] = Field(default_factory=list)
    environment_alignment: float = Field(default=0.0, ge=0, le=1)
    planning_alignment: float = Field(default=0.0, ge=0, le=1)


class DecisionScore(BaseModel):
    """决策质量评分。"""

    decision_score: float = Field(default=0.0, ge=0, le=1)
    environment_alignment: float = Field(default=0.0, ge=0, le=1)
    planning_alignment: float = Field(default=0.0, ge=0, le=1)
    risk_awareness: float = Field(default=0.0, ge=0, le=1)
    historical_success: float = Field(default=0.0, ge=0, le=1)
    components: dict = Field(default_factory=dict)


class DecisionRiskNotes(BaseModel):
    """决策风险融合结果。"""

    risk_level: str = ""
    risk_notes: list[str] = Field(default_factory=list)
    avoid_options: list[str] = Field(default_factory=list)
    alternative_suggestions: list[str] = Field(default_factory=list)
