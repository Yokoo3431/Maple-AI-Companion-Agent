"""Quest Plan 数据模型(Phase 2-C,任务语义动作,非真实输入)。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class QuestPlanAction(StrEnum):
    """任务语义动作(仅计划语义,禁止物理动作)。"""

    ANALYZE = "ANALYZE"
    MOVE_HINT = "MOVE_HINT"
    TALK = "TALK"
    COLLECT = "COLLECT"
    DEFEAT = "DEFEAT"
    DELIVER = "DELIVER"
    COMPLETE = "COMPLETE"


class QuestPlanStatus(StrEnum):
    """任务计划状态。"""

    CREATED = "CREATED"
    READY = "READY"
    FAILED = "FAILED"


class QuestPlanStep(BaseModel):
    """任务计划步骤。"""

    step_id: str
    action: QuestPlanAction
    description: str
    target: str = ""
    related_map: int | str | None = None
    related_npc: int | str | None = None
    related_monster: int | str | None = None
    prerequisite: int | str | None = None
    expected_result: str = ""


class QuestPlan(BaseModel):
    """任务计划(Goal → Quest → 步骤)。"""

    plan_id: str
    goal_id: str = ""
    quest_id: int | str
    title: str
    steps: list[QuestPlanStep] = Field(default_factory=list)
    status: QuestPlanStatus = QuestPlanStatus.READY
    confidence: float = Field(default=1.0, ge=0, le=1)
    trace_id: str = ""
