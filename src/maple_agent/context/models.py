"""AgentContext 领域模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field

from maple_agent.executor.models import ExecutionResult
from maple_agent.fusion.models import WorldState
from maple_agent.goal.models import Goal
from maple_agent.quest.models import Quest
from maple_agent.quest_planner.models import QuestPlan


class GoalContext(BaseModel):
    """目标上下文(Goal + Quest),与 WorldState 分离。"""

    active_quest: Quest | None = None
    available_quests: list[Quest] = Field(default_factory=list)
    completed_quest_ids: list[int | str] = Field(default_factory=list)
    active_goal: Goal | None = None
    candidate_goals: list[Goal] = Field(default_factory=list)
    goal_history: list[Goal] = Field(default_factory=list)
    trace_id: str = ""


class QuestPlanContext(BaseModel):
    """任务计划上下文(实现目标的方法),与 WorldState / Goal 分离。"""

    active_quest_plan: QuestPlan | None = None
    current_step: int = 0
    plan_history: list[QuestPlan] = Field(default_factory=list)


class ExecutionContext(BaseModel):
    """执行上下文(仅记录 Mock 执行结果,WorldState 不变)。"""

    last_execution: ExecutionResult | None = None
    execution_history: list[ExecutionResult] = Field(default_factory=list)


class AgentContext(BaseModel):
    """Planner 前统一上下文(Vision + Knowledge + Runtime)。"""

    world_state: WorldState | None = None
    runtime_state: str = ""
    vision_summary: str = ""
    knowledge_profile: str = ""
    goal_context: GoalContext | None = None
    quest_plan_context: QuestPlanContext | None = None
    execution_context: ExecutionContext | None = None
    trace_id: str = ""
