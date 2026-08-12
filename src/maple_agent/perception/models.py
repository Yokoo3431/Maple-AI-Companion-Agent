"""Perception Binding 数据模型(Phase 9-E,视觉观察参考,只读)。"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ObservationSource(StrEnum):
    """观察来源。"""

    MOCK_SCREENSHOT = "MOCK_SCREENSHOT"
    WINDOW_CAPTURE_REFERENCE = "WINDOW_CAPTURE_REFERENCE"
    IMAGE_REFERENCE = "IMAGE_REFERENCE"


class PerceivedEntityType(StrEnum):
    """感知实体类型。"""

    NPC = "NPC"
    MONSTER = "MONSTER"
    PLAYER = "PLAYER"
    ITEM = "ITEM"
    UI_ELEMENT = "UI_ELEMENT"
    MAP_LABEL = "MAP_LABEL"
    UNKNOWN = "UNKNOWN"


class VisualObservation(BaseModel):
    """一次视觉观察快照(仅参考)。"""

    observation_id: str
    source: ObservationSource
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    image_reference: str = ""
    resolution: dict = Field(default_factory=dict)
    confidence: float = Field(default=0.0, ge=0, le=1)
    detected_elements: list[str] = Field(default_factory=list)
    context: dict = Field(default_factory=dict)


class PerceivedEntity(BaseModel):
    """视觉识别对象(位置仅参考,不生成点击坐标)。"""

    entity_id: str
    entity_type: PerceivedEntityType
    name: str
    position_reference: dict = Field(default_factory=dict)
    confidence: float = Field(default=0.0, ge=0, le=1)
    attributes: dict = Field(default_factory=dict)


class MaplePerceptionReference(BaseModel):
    """感知参考(不是 Action)。"""

    observation_id: str = ""
    visible_entities: list[PerceivedEntity] = Field(default_factory=list)
    visible_map: str = ""
    ui_state_reference: dict = Field(default_factory=dict)
    related_knowledge: dict = Field(default_factory=dict)
    confidence: float = Field(default=0.0, ge=0, le=1)
    reasoning: list[str] = Field(default_factory=list)
