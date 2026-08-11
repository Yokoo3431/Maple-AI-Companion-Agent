"""Human Alignment 数据模型(Phase 8-F,用户对齐决策优化,只读)。"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from maple_agent.decision_reference.models import ReferenceOption


class FeedbackAction(StrEnum):
    """用户反馈动作。"""

    ACCEPT = "accept"
    REJECT = "reject"
    CORRECT = "correct"


class HumanFeedback(BaseModel):
    """用户反馈。"""

    feedback_id: str
    option_id: str = ""
    action: FeedbackAction = FeedbackAction.ACCEPT
    comment: str = ""
    trace_id: str = ""


class PreferenceRecord(BaseModel):
    """偏好记忆记录。"""

    record_id: str
    option_id: str = ""
    action: str = ""
    reason: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class HumanAlignedDecisionReference(BaseModel):
    """对齐后的决策参考(仍非 Action)。"""

    preferred_options: list[ReferenceOption] = Field(default_factory=list)
    rejected_options: list[str] = Field(default_factory=list)
    alignment_score: float = Field(default=0.0, ge=0, le=1)
    adjustments: list[str] = Field(default_factory=list)
    reasoning: list[str] = Field(default_factory=list)


class AlignmentScore(BaseModel):
    """对齐评分。"""

    alignment_score: float = Field(default=0.0, ge=0, le=1)
    preference_match: float = Field(default=0.0, ge=0, le=1)
    historical_approval: float = Field(default=0.0, ge=0, le=1)
    decision_quality: float = Field(default=0.0, ge=0, le=1)
    risk_compatibility: float = Field(default=0.0, ge=0, le=1)
    components: dict = Field(default_factory=dict)


class PreferenceUpdateReference(BaseModel):
    """反馈处理结果。"""

    feedback_id: str = ""
    updates: list[str] = Field(default_factory=list)
    applied: bool = False
