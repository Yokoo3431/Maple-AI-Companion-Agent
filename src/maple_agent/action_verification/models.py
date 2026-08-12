"""Action Outcome Verification 数据模型(Phase 13-C,动作结果验证参考,只读)。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ActionOutcomeStatus(StrEnum):
    """动作结果状态。"""

    NOT_EVALUATED = "NOT_EVALUATED"
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    INCONCLUSIVE = "INCONCLUSIVE"
    BLOCKED = "BLOCKED"


class ExpectedOutcomeReference(BaseModel):
    """预期结果参考(不是 Executor Contract)。"""

    expectation_id: str
    action_id: str = ""
    action_reference: str = ""
    action_type: str = ""
    target_reference: str = ""
    expected_map: str = ""
    expected_target_visible: bool = False
    expected_target_absent: bool = False
    expected_quest_progress: list[str] = Field(default_factory=list)
    expected_state_changes: list[str] = Field(default_factory=list)
    expected_ui_signals: list[str] = Field(default_factory=list)
    timeout_reference_seconds: float = Field(default=30.0, ge=0)
    confidence: float = Field(default=0.0, ge=0, le=1)
    reasoning: list[str] = Field(default_factory=list)


class OutcomeEvidence(BaseModel):
    """结果证据。"""

    evidence_type: str
    before_value: str = ""
    after_value: str = ""
    matched: bool = False
    confidence: float = Field(default=0.0, ge=0, le=1)
    reason: str = ""


class ActionOutcomeReference(BaseModel):
    """动作结果验证参考(只验证,不执行)。"""

    outcome_id: str
    source_action: str = ""
    status: ActionOutcomeStatus = ActionOutcomeStatus.NOT_EVALUATED
    expected_outcome: ExpectedOutcomeReference | None = None
    evidence: list[OutcomeEvidence] = Field(default_factory=list)
    matched_conditions: list[str] = Field(default_factory=list)
    unmatched_conditions: list[str] = Field(default_factory=list)
    elapsed_reference: float = Field(default=0.0, ge=0)
    confidence: float = Field(default=0.0, ge=0, le=1)
    reasoning: list[str] = Field(default_factory=list)
    recovery_required: bool = False
