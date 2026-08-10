"""Vision Evaluation 数据模型(Phase 6-B,视觉识别质量评估,只读)。"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class RiskLevel(StrEnum):
    """视觉评估风险等级。"""

    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class VisionMetric(BaseModel):
    """单项视觉指标。"""

    metric_name: str
    score: float = Field(default=0.0, ge=0, le=1)
    reason: str = ""


class VisionEvaluationResult(BaseModel):
    """视觉识别评估结果。"""

    evaluation_id: str
    frame_id: str = ""
    overall_score: float = Field(default=0.0, ge=0, le=1)
    ocr_score: float = Field(default=0.0, ge=0, le=1)
    entity_score: float = Field(default=0.0, ge=0, le=1)
    consistency_score: float = Field(default=0.0, ge=0, le=1)
    confidence_score: float = Field(default=0.0, ge=0, le=1)
    risk_level: RiskLevel = RiskLevel.LOW
    issues: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class VisionBenchmarkCase(BaseModel):
    """视觉评测用例。"""

    case_id: str
    ocr_text: str = ""
    confidence: float = Field(default=0.0, ge=0, le=1)
    map_name: str = ""
    entities: list[str] = Field(default_factory=list)
    expected_score: float = Field(default=0.0, ge=0, le=1)
    expected_risk: RiskLevel = RiskLevel.LOW
    source: str = ""


class VisionBenchmarkResult(BaseModel):
    """视觉评测集汇总。"""

    total_cases: int = 0
    passed: int = 0
    accuracy: float = Field(default=0.0, ge=0, le=1)
    average_score: float = Field(default=0.0, ge=0, le=1)
    failure_count: int = 0
    failures: list[str] = Field(default_factory=list)
