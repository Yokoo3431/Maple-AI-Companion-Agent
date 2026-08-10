"""Experience 领域模型(Phase 5-E,结构化经验库,非训练)。"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class ExperienceRecord(BaseModel):
    """一次执行经验的完整记录。"""

    experience_id: str
    context_snapshot: dict = Field(default_factory=dict)
    goal: str = ""
    action: str = ""
    result: str = ""
    reflection: str = ""
    success: bool = False
    failure_type: str = ""
    resolution: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    trace_id: str = ""
