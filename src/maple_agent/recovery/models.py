"""Failure Recovery 数据模型(Phase 13-B,失败检测与恢复建议,只读)。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class FailureType(StrEnum):
    """失败类型。"""

    NAVIGATION_TIMEOUT = "NAVIGATION_TIMEOUT"
    STATE_MISMATCH = "STATE_MISMATCH"
    COMBAT_FAILURE = "COMBAT_FAILURE"
    SAFETY_BLOCKED = "SAFETY_BLOCKED"
    UNKNOWN = "UNKNOWN"


class RecoveryType(StrEnum):
    """恢复建议类型(不是执行命令)。"""

    RETRY_REFERENCE = "RETRY_REFERENCE"
    WAIT_OBSERVATION_REFERENCE = "WAIT_OBSERVATION_REFERENCE"
    REPLAN_REFERENCE = "REPLAN_REFERENCE"
    CHANGE_TARGET_REFERENCE = "CHANGE_TARGET_REFERENCE"
    ABORT_REFERENCE = "ABORT_REFERENCE"


class RecoveryReference(BaseModel):
    """恢复建议参考(只分析失败,不执行恢复)。"""

    recovery_id: str
    source_action: str = ""
    failure_type: FailureType = FailureType.UNKNOWN
    recovery_type: RecoveryType = RecoveryType.WAIT_OBSERVATION_REFERENCE
    reasoning: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0, le=1)
    validation: str = ""
