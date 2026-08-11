"""Environment State 数据模型(Phase 8-A,环境状态建模,只读)。"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class EnvironmentState(BaseModel):
    """结构化环境状态。"""

    environment_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    location: str = ""
    visible_entities: list[str] = Field(default_factory=list)
    resources: list[str] = Field(default_factory=list)
    conditions: dict = Field(default_factory=dict)
    world_context: str = ""
    confidence: float = Field(default=0.0, ge=0, le=1)


class EnvironmentSnapshot(BaseModel):
    """环境状态快照(before/after/changes)。"""

    before_state: EnvironmentState | None = None
    after_state: EnvironmentState | None = None
    changes: list[str] = Field(default_factory=list)
    trace_id: str = ""
