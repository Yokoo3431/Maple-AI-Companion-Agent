"""Observation 沙箱数据模型(Phase 6-A,只读观察,禁止输入控制)。"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class ObservationFrame(BaseModel):
    """标准化观察帧(截图 + OCR 结果)。"""

    frame_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source: str = ""
    image_available: bool = False
    ocr_text: str = ""
    confidence: float = Field(default=0.0, ge=0, le=1)
    metadata: dict = Field(default_factory=dict)


class ObservationState(BaseModel):
    """观察状态(地图/实体/置信度摘要)。"""

    map_name: str = ""
    visible_entities: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0, le=1)
    observations: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
