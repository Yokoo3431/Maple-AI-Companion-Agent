"""Perception Fusion 数据模型(Phase 10-A,多源感知融合参考,只读)。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class FusionSourceInput(BaseModel):
    """单个融合来源(仅参考快照)。"""

    source: str
    confidence: float = Field(default=0.0, ge=0, le=1)
    summary: str = ""


class PerceptionFusionReference(BaseModel):
    """统一感知融合参考(不是 Action)。"""

    fusion_id: str
    source_inputs: list[FusionSourceInput] = Field(default_factory=list)
    fused_confidence: float = Field(default=0.0, ge=0, le=1)
    consistency_score: float = Field(default=0.0, ge=0, le=1)
    conflicts: list[str] = Field(default_factory=list)
    missing_signals: list[str] = Field(default_factory=list)
    focus_reference: str = ""
    reasoning: list[str] = Field(default_factory=list)
    external_source_reference: list[str] = Field(default_factory=list)
