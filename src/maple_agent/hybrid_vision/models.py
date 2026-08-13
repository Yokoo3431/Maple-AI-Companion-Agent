"""Hybrid Local Perception 数据模型(Phase 13-I.1,只读感知证据)。"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class PerceptionMethod(StrEnum):
    """感知证据方法(OCR 只是其中一种)。"""

    TEMPLATE = "TEMPLATE"
    COLOR_GEOMETRY = "COLOR_GEOMETRY"
    OCR = "OCR"
    LOCAL_CLASSIFIER = "LOCAL_CLASSIFIER"
    LOCAL_DETECTOR = "LOCAL_DETECTOR"
    SCREEN_PARSER = "SCREEN_PARSER"
    KNOWLEDGE_RESOLUTION = "KNOWLEDGE_RESOLUTION"


class CaptureCondition(StrEnum):
    """捕获条件(四种独立状态,禁止合并报告)。"""

    FOREGROUND = "FOREGROUND"
    BACKGROUND_VISIBLE = "BACKGROUND_VISIBLE"
    BACKGROUND_OCCLUDED = "BACKGROUND_OCCLUDED"
    MINIMIZED = "MINIMIZED"


class PerceptionEvidence(BaseModel):
    """统一感知证据(最小兼容扩展,可流入现有 VisualObservation/Fusion)。"""

    evidence_id: str
    evidence_type: str
    roi: dict = Field(default_factory=dict)
    value: str | float | bool | None = None
    canonical_candidate_id: str = ""
    confidence: float = Field(default=0.0, ge=0, le=1)
    source: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    frame_id: str = ""
    method: PerceptionMethod = PerceptionMethod.OCR
    raw_value: str = ""


class ChangeResult(BaseModel):
    """帧/ROI 变化检测结果。"""

    frame_id: str = ""
    changed: bool = False
    score: float = Field(default=0.0, ge=0, le=1)
    roi_scores: dict[str, float] = Field(default_factory=dict)
    method: str = ""
    latency_ms: float | None = None


class HpMpGeometryResult(BaseModel):
    """HP/MP 几何提取结果(主路径,不依赖数字 OCR)。"""

    hp_ratio: float | None = Field(default=None, ge=0, le=1)
    mp_ratio: float | None = Field(default=None, ge=0, le=1)
    hp_confidence: float = Field(default=0.0, ge=0, le=1)
    mp_confidence: float = Field(default=0.0, ge=0, le=1)
    method: str = "color_geometry"
    latency_ms: float | None = None
    reasons: list[str] = Field(default_factory=list)


class TemplateMatch(BaseModel):
    """模板匹配结果。"""

    template_id: str = ""
    score: float = Field(default=0.0, ge=0, le=1)
    location: dict = Field(default_factory=dict)
    latency_ms: float | None = None
    matched: bool = False


class TemplateDiscrimination(BaseModel):
    """多模板判别(top1/top2/margin,防误报)。"""

    query_id: str = ""
    top1: TemplateMatch | None = None
    top2: TemplateMatch | None = None
    margin: float = Field(default=0.0, ge=0, le=1)
    matched: bool = False
    canonical_candidate_id: str = ""
    reason: str = ""


class ResolutionResult(BaseModel):
    """Knowledge-guided canonical resolution(Knowledge 不能伪造观察)。"""

    resolved: bool = False
    canonical_candidate_id: str = ""
    display_name: str = ""
    confidence: float = Field(default=0.0, ge=0, le=1)
    method: PerceptionMethod = PerceptionMethod.KNOWLEDGE_RESOLUTION
    source: str = ""
    reasoning: list[str] = Field(default_factory=list)


class PlannedVisionTask(BaseModel):
    """事件驱动调度产出:哪个 ROI 用哪个方法运行。"""

    roi: str = ""
    method: PerceptionMethod = PerceptionMethod.OCR
    reason: str = ""
    priority: int = Field(default=0, ge=0)
