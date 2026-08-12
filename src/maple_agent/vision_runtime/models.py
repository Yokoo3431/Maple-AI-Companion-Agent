"""Vision Runtime 数据模型(Phase 11-A,窗口视觉读取与结构化观察,只读)。"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class VisionSource(StrEnum):
    """视觉来源。"""

    MOCK_SCREENSHOT = "MOCK_SCREENSHOT"
    WINDOW_CAPTURE_REFERENCE = "WINDOW_CAPTURE_REFERENCE"
    IMAGE_REFERENCE = "IMAGE_REFERENCE"


class VisionFrame(BaseModel):
    """一帧窗口视觉快照。"""

    frame_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    source: VisionSource = VisionSource.MOCK_SCREENSHOT
    image_reference: str = ""
    confidence: float = Field(default=0.0, ge=0, le=1)


class CaptureReference(BaseModel):
    """截图来源元数据(窗口信息仅参考)。"""

    capture_id: str
    source: str = ""
    window_title: str = ""
    window_rect: dict = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    confidence: float = Field(default=0.0, ge=0, le=1)


class OcrResult(BaseModel):
    """OCR 识别结果。"""

    text: str = ""
    lines: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0, le=1)
    source: str = ""


class DetectedElement(BaseModel):
    """画面元素(确定性分类)。"""

    element_type: str = "UNKNOWN"
    name: str = ""
    confidence: float = Field(default=0.0, ge=0, le=1)


class ScreenObservation(BaseModel):
    """结构化屏幕观察(不是 Action)。"""

    visible_map: str = ""
    visible_entities: list[str] = Field(default_factory=list)
    ui_elements: list[str] = Field(default_factory=list)
    hp_reference: float | None = Field(default=None, ge=0, le=1)
    mp_reference: float | None = Field(default=None, ge=0, le=1)
    quest_reference: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0, le=1)
