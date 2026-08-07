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


class MatchedEntity(BaseModel):
    """知识图谱匹配到的实体。"""

    entity_type: str
    entity_id: int | str
    name: str
    confidence: float = Field(default=0.0, ge=0, le=1)


class RetrievalMetrics(BaseModel):
    """检索指标。"""

    candidate_count: int = 0
    best_score: float = Field(default=0.0, ge=0, le=1)
    confidence_level: str = "LOW"
    ranking_method: str = ""


class KnowledgeState(BaseModel):
    """知识理解状态(与 WorldState 分离,记录匹配来源)。"""

    matched_entities: list[MatchedEntity] = Field(default_factory=list)
    top_candidates: list[MatchedEntity] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0, le=1)
    source: str = ""
    selection_reason: str = ""
    retrieval_metrics: RetrievalMetrics | None = None


class AgentContext(BaseModel):
    """Planner 前统一上下文(Vision + Knowledge + Runtime)。"""

    world_state: WorldState | None = None
    runtime_state: str = ""
    vision_summary: str = ""
    knowledge_profile: str = ""
    goal_context: GoalContext | None = None
    quest_plan_context: QuestPlanContext | None = None
    execution_context: ExecutionContext | None = None
    knowledge_state: KnowledgeState | None = None
    trace_id: str = ""
