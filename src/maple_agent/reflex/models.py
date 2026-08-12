"""L1 Reflex 数据模型(Phase 10-B,快速状态感知参考,只读)。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ReflexStateType(StrEnum):
    """反射状态(感知结论,不是 Action)。"""

    UNKNOWN = "UNKNOWN"
    NORMAL = "NORMAL"
    LOW_HP = "LOW_HP"
    LOW_MP = "LOW_MP"
    DANGER = "DANGER"
    DEATH = "DEATH"
    UI_ALERT = "UI_ALERT"


class DangerEventType(StrEnum):
    """危险事件类型。"""

    HP_LOW = "HP_LOW"
    MP_LOW = "MP_LOW"
    DEATH = "DEATH"
    STATUS_ABNORMAL = "STATUS_ABNORMAL"
    UI_ALERT = "UI_ALERT"


class HpMpReference(BaseModel):
    """HP/MP 状态参考(仅参考)。"""

    current_value: int | None = None
    max_value: int | None = None
    ratio: float | None = Field(default=None, ge=0, le=1)
    confidence: float = Field(default=0.0, ge=0, le=1)
    source: str = ""


class DangerEventReference(BaseModel):
    """危险事件参考(只报告,不执行)。"""

    event_id: str
    event_type: DangerEventType
    severity: float = Field(default=0.0, ge=0, le=1)
    source: str = ""
    confidence: float = Field(default=0.0, ge=0, le=1)
    reasoning: str = ""


class ReflexReference(BaseModel):
    """L1 Reflex 输出(Reference Only,不是 Action / Command)。"""

    reflex_id: str
    state: ReflexStateType = ReflexStateType.UNKNOWN
    hp_reference: HpMpReference | None = None
    mp_reference: HpMpReference | None = None
    danger_events: list[DangerEventReference] = Field(
        default_factory=list
    )
    ui_alerts: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0, le=1)
    reasoning: list[str] = Field(default_factory=list)
    validation: str = ""
