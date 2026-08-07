"""事件领域模型:强类型 Event、EventType 枚举、Priority 枚举。"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class EventType(StrEnum):
    """系统内事件类型。"""

    # Runtime
    START = "runtime.start"
    STARTING = "runtime.starting"
    READY = "runtime.ready"
    RUNNING = "runtime.running"
    PAUSE = "runtime.pause"
    STOP = "runtime.stop"
    STOPPING = "runtime.stopping"
    STOPPED = "runtime.stopped"

    # Vision
    SCREEN_CAPTURED = "vision.screen_captured"
    SCREEN_UPDATED = "vision.screen_updated"
    OCR_COMPLETED = "vision.ocr_completed"
    HP_LOW = "vision.hp_low"
    GAME_WINDOW_LOST = "vision.game_window_lost"

    # Agent
    OBSERVE_STARTED = "agent.observe.started"
    CONTEXT_READY = "agent.context.ready"
    LOOP_PLAN_CREATED = "agent.plan.created"
    PLAN_VALIDATED = "agent.plan.validated"
    LOOP_ERROR = "agent.loop.error"
    GOAL_SELECTED = "agent.goal.selected"
    GOAL_CHANGED = "agent.goal.changed"
    GOAL_COMPLETED = "agent.goal.completed"
    QUEST_PLAN_CREATED = "agent.quest_plan.created"
    QUEST_PLAN_VALIDATED = "agent.quest_plan.validated"
    QUEST_PLAN_FAILED = "agent.quest_plan.failed"
    PLAN_CREATED = "agent.plan_created"
    PLAN_FAILED = "agent.plan_failed"

    # Error
    ERROR_OCCURRED = "error.occurred"

    # Storage
    STORAGE_SAVED = "storage.saved"
    STORAGE_LOADED = "storage.loaded"


class Priority(StrEnum):
    """事件优先级(数值越大越先处理)。"""

    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    NORMAL = "NORMAL"
    LOW = "LOW"


_PRIORITY_ORDER: dict[Priority, int] = {
    Priority.CRITICAL: 3,
    Priority.HIGH: 2,
    Priority.NORMAL: 1,
    Priority.LOW: 0,
}

_DEFAULT_PRIORITY: dict[EventType, Priority] = {
    EventType.ERROR_OCCURRED: Priority.CRITICAL,
    EventType.GAME_WINDOW_LOST: Priority.HIGH,
    EventType.HP_LOW: Priority.HIGH,
    EventType.PLAN_FAILED: Priority.HIGH,
    EventType.START: Priority.NORMAL,
    EventType.STARTING: Priority.NORMAL,
    EventType.READY: Priority.NORMAL,
    EventType.RUNNING: Priority.NORMAL,
    EventType.PAUSE: Priority.NORMAL,
    EventType.STOP: Priority.NORMAL,
    EventType.STOPPING: Priority.NORMAL,
    EventType.STOPPED: Priority.NORMAL,
    EventType.SCREEN_UPDATED: Priority.LOW,
    EventType.SCREEN_CAPTURED: Priority.LOW,
    EventType.OCR_COMPLETED: Priority.LOW,
    EventType.PLAN_CREATED: Priority.NORMAL,
    EventType.STORAGE_SAVED: Priority.NORMAL,
    EventType.STORAGE_LOADED: Priority.NORMAL,
    EventType.OBSERVE_STARTED: Priority.NORMAL,
    EventType.CONTEXT_READY: Priority.NORMAL,
    EventType.LOOP_PLAN_CREATED: Priority.NORMAL,
    EventType.PLAN_VALIDATED: Priority.NORMAL,
    EventType.LOOP_ERROR: Priority.HIGH,
    EventType.GOAL_SELECTED: Priority.NORMAL,
    EventType.GOAL_CHANGED: Priority.NORMAL,
    EventType.GOAL_COMPLETED: Priority.NORMAL,
    EventType.QUEST_PLAN_CREATED: Priority.NORMAL,
    EventType.QUEST_PLAN_VALIDATED: Priority.NORMAL,
    EventType.QUEST_PLAN_FAILED: Priority.HIGH,
}


def priority_order(priority: Priority) -> int:
    """返回优先级的数值排序键。"""
    return _PRIORITY_ORDER[priority]


class Event(BaseModel):
    """强类型事件模型(禁止裸 dict 作为 payload)。"""

    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(default_factory=lambda: uuid.uuid4().hex[:16])
    event_type: EventType
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    priority: Priority = Priority.NORMAL
    trace_id: str = ""
    source: str = ""
    payload: BaseModel | None = None

    @field_validator("payload", mode="before")
    @classmethod
    def _reject_bare_dict(cls, value: object) -> object:
        if isinstance(value, dict):
            raise ValueError("payload 必须是强类型模型,禁止裸 dict")
        return value

    @classmethod
    def create(
        cls,
        event_type: EventType,
        *,
        source: str,
        payload: BaseModel | None = None,
        priority: Priority | None = None,
        trace_id: str | None = None,
    ) -> Event:
        """构造事件;trace_id 缺省时自动取自当前日志追踪上下文。"""
        from maple_agent.logging_setup import TraceContext  # 延迟导入,避免循环依赖

        current_trace, _ = TraceContext.current()
        resolved_priority = (
            priority
            if priority is not None
            else _DEFAULT_PRIORITY.get(event_type, Priority.NORMAL)
        )
        return cls(
            event_type=event_type,
            source=source,
            payload=payload,
            priority=resolved_priority,
            trace_id=trace_id if trace_id is not None else current_trace,
        )
