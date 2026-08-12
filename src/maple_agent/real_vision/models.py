"""Real Vision Validation 数据模型(Phase 13-F,真实只读视觉验证)。"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class CaptureStatus(StrEnum):
    """捕获状态。"""

    OK = "OK"
    WINDOW_NOT_FOUND = "WINDOW_NOT_FOUND"
    WINDOW_INVALID = "WINDOW_INVALID"
    CAPTURE_FAILED = "CAPTURE_FAILED"
    UNAVAILABLE = "UNAVAILABLE"


class VisionGroundTruth(BaseModel):
    """样本真值(允许字段为空,不伪造)。"""

    map_name: str = ""
    aliases: list[str] = Field(default_factory=list)
    hp: float | None = Field(default=None, ge=0, le=1)
    mp: float | None = Field(default=None, ge=0, le=1)
    visible_npcs: list[str] = Field(default_factory=list)
    visible_monsters: list[str] = Field(default_factory=list)
    visible_items: list[str] = Field(default_factory=list)
    quest_state: str = ""
    ui_signals: list[str] = Field(default_factory=list)


class VisionValidationSample(BaseModel):
    """真实视觉验证样本。"""

    sample_id: str
    source_type: str = "real"
    game_profile: str = ""
    server_profile: str = ""
    resolution: str = ""
    window_mode: str = ""
    dpi_scale: float = Field(default=1.0, ge=0)
    image_reference: str = ""
    ground_truth: VisionGroundTruth = Field(
        default_factory=VisionGroundTruth
    )
    captured_at: datetime | None = None
    notes: str = ""


class ConfidenceBucket(BaseModel):
    """置信度分桶。"""

    bucket: str
    sample_count: int = 0
    accuracy: float | None = None


class RealVisionBenchmarkResult(BaseModel):
    """真实视觉 Benchmark 结果(无法评估项输出 None,不冒充已测)。"""

    sample_count: int = 0
    map_accuracy: float | None = None
    map_exact_accuracy: float | None = None
    map_alias_accuracy: float | None = None
    hp_mae: float | None = None
    mp_mae: float | None = None
    npc_precision: float | None = None
    npc_recall: float | None = None
    monster_precision: float | None = None
    monster_recall: float | None = None
    item_precision: float | None = None
    item_recall: float | None = None
    quest_state_accuracy: float | None = None
    ui_signal_accuracy: float | None = None
    capture_success_rate: float | None = None
    ocr_success_rate: float | None = None
    mean_capture_latency_ms: float | None = None
    p50_capture_latency_ms: float | None = None
    p95_capture_latency_ms: float | None = None
    mean_ocr_latency_ms: float | None = None
    p50_ocr_latency_ms: float | None = None
    p95_ocr_latency_ms: float | None = None
    mean_e2e_latency_ms: float | None = None
    p50_e2e_latency_ms: float | None = None
    p95_e2e_latency_ms: float | None = None
    max_e2e_latency_ms: float | None = None
    failure_taxonomy: dict[str, int] = Field(default_factory=dict)
    confidence_calibration_status: str = "NOT_CALIBRATED"
    confidence_buckets: list[ConfidenceBucket] = Field(
        default_factory=list
    )
    reasons: list[str] = Field(default_factory=list)


class RealVisionReadinessPolicy(BaseModel):
    """真实视觉就绪阈值(集中配置,禁止散落 magic number)。"""

    minimum_sample_count: int = Field(default=10, ge=1)
    capture_success_rate: float = Field(default=0.98, ge=0, le=1)
    map_accuracy: float = Field(default=0.95, ge=0, le=1)
    hp_mp_accuracy: float = Field(default=0.95, ge=0, le=1)
    quest_state_accuracy: float = Field(default=0.90, ge=0, le=1)
    ui_signal_accuracy: float = Field(default=0.85, ge=0, le=1)
    confidence_calibration: float = Field(default=0.70, ge=0, le=1)
    entity_detection_required: bool = False

    @classmethod
    def from_dict(cls, data: dict | None) -> RealVisionReadinessPolicy:
        if not data:
            return cls()
        fields = set(cls.model_fields)
        return cls(
            **{
                key: value
                for key, value in data.items()
                if key in fields
            }
        )

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")
