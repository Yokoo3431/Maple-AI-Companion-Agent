"""Dynamic World Model 数据模型(Phase 8-B,环境动态理解,只读)。"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field

from maple_agent.environment.models import EnvironmentState


class WorldEventType(StrEnum):
    """环境事件类型。"""

    ENTITY_APPEARED = "ENTITY_APPEARED"
    ENTITY_DISAPPEARED = "ENTITY_DISAPPEARED"
    LOCATION_CHANGED = "LOCATION_CHANGED"
    RESOURCE_CHANGED = "RESOURCE_CHANGED"
    CONDITION_CHANGED = "CONDITION_CHANGED"


class EnvironmentEvent(BaseModel):
    """环境变化事件。"""

    event_type: WorldEventType
    detail: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class EnvironmentTransition(BaseModel):
    """环境状态转换。"""

    from_state: EnvironmentState | None = None
    to_state: EnvironmentState | None = None
    changes: list[str] = Field(default_factory=list)
    transition_type: str = ""
    confidence: float = Field(default=0.0, ge=0, le=1)


class EnvironmentHistory(BaseModel):
    """环境历史时间序列。"""

    history_id: str
    environment_id: str = ""
    snapshots: list[EnvironmentState] = Field(default_factory=list)
    timeline: list[EnvironmentEvent] = Field(default_factory=list)
    trace_id: str = ""


class PredictedEnvironmentState(BaseModel):
    """预测环境状态(仅参考,禁止修改真实状态)。"""

    predicted_location: str = ""
    predicted_entities: list[str] = Field(default_factory=list)
    predicted_resources: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0, le=1)
    reasoning: list[str] = Field(default_factory=list)
    summary: str = ""
