"""Reflection 领域模型(Phase 5-D,闭环反思,禁止真实执行)。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class FailureType(StrEnum):
    """反思失败类型。"""

    WORLD_MISMATCH = "WORLD_MISMATCH"
    KNOWLEDGE_ERROR = "KNOWLEDGE_ERROR"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    EXECUTION_FAILED = "EXECUTION_FAILED"
    OBSERVATION_FAILED = "OBSERVATION_FAILED"


class ReflectionResult(BaseModel):
    """一次执行后的反思结果。"""

    reflection_id: str
    execution_id: str = ""
    expected_result: str = ""
    actual_result: str = ""
    success: bool = False
    failure_type: FailureType | None = None
    failure_reason: str = ""
    confidence: float = Field(default=0.0, ge=0, le=1)
    next_action: str = "continue"
    state_update: str = "rejected"
    trace_id: str = ""


class ReflectionState(BaseModel):
    """挂载到 AgentContext 的反思状态。"""

    last_reflection: ReflectionResult | None = None
    failure_history: list[ReflectionResult] = Field(default_factory=list)
    retry_count: int = 0
    confidence: float = Field(default=0.0, ge=0, le=1)
