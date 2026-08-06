"""Vision 领域模型(ScreenFrame → Observation → VisionState),全部强类型。"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator

from maple_agent.game.window import WindowInfo


class ScreenFrame(BaseModel):
    """一次截图的元信息(不含像素;像素文件按 ScreenshotPolicy 落盘)。"""

    frame_id: str
    trace_id: str = ""
    captured_at: datetime
    window: WindowInfo | None = None
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    dpi_scale: float = Field(default=1.0, gt=0)
    image_path: str = ""
    source_provider: str = ""


class Observation(BaseModel):
    """单个元素的原始识别结果(Phase 1.1 尚无真实识别,模型预留)。"""

    element: str
    type: Literal["number", "text", "bar_ratio", "boolean"] = "text"
    raw_value: str = ""
    normalized_value: str | int | float | bool
    confidence: float = Field(default=0.0, ge=0, le=1)
    source: str = ""

    @field_validator("normalized_value", mode="before")
    @classmethod
    def _reject_bare_dict(cls, value: object) -> object:
        if isinstance(value, dict):
            raise ValueError("normalized_value 必须是标量,禁止裸 dict")
        return value


class ObservationRef(BaseModel):
    """Observation 的精简引用(供 VisionState 摘要)。"""

    element: str
    normalized_value: str | int | float | bool
    confidence: float


class VisionState(BaseModel):
    """聚合识别摘要;不承载全部原始识别结果(明细见 Observation / Session Replay)。"""

    frame_id: str
    trace_id: str = ""
    hp: int | None = None
    mp: int | None = None
    map_name: str | None = None
    map_id: int | str | None = None
    region: str = ""
    map_confidence: float | None = None
    summary: str = ""
    observation_refs: list[ObservationRef] = Field(default_factory=list)
    overall_confidence: float | None = Field(default=None, ge=0, le=1)
