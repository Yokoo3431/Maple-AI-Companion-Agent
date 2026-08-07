"""AgentContext 领域模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field

from maple_agent.fusion.models import WorldState
from maple_agent.quest.models import Quest


class GoalContext(BaseModel):
    """目标上下文(任务领域),与 WorldState 分离。"""

    active_quest: Quest | None = None
    available_quests: list[Quest] = Field(default_factory=list)
    completed_quest_ids: list[int | str] = Field(default_factory=list)
    trace_id: str = ""


class AgentContext(BaseModel):
    """Planner 前统一上下文(Vision + Knowledge + Runtime)。"""

    world_state: WorldState | None = None
    runtime_state: str = ""
    vision_summary: str = ""
    knowledge_profile: str = ""
    goal_context: GoalContext | None = None
    trace_id: str = ""
