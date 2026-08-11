"""Maple Companion Cognitive Context 数据模型(Phase 9-C,统一认知快照,只读)。"""

from __future__ import annotations

from pydantic import BaseModel, Field

from maple_agent.environment.models import EnvironmentState
from maple_agent.world_model.models import PredictedEnvironmentState


class MaplePlayerContext(BaseModel):
    """玩家上下文(仅参考数据,无游戏内存读取)。"""

    player_id: str = ""
    level: int = 0
    job: str = ""
    location: str = ""
    current_hp_reference: int | None = None
    current_mp_reference: int | None = None
    inventory_reference: list[str] = Field(default_factory=list)
    quest_reference: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0, le=1)


class MapleWorldContext(BaseModel):
    """世界上下文(聚合环境/世界模型/推理)。"""

    location: str = ""
    environment_state: EnvironmentState | None = None
    world_prediction: PredictedEnvironmentState | None = None
    visible_entities: list[str] = Field(default_factory=list)
    world_events: list[str] = Field(default_factory=list)
    environment_risk: str = ""
    confidence: float = Field(default=0.0, ge=0, le=1)


class MapleGoalContext(BaseModel):
    """目标上下文(聚合目标/调度/规划/决策参考)。"""

    active_goal: str = ""
    goal_type: str = ""
    priority: int = 0
    related_tasks: list[str] = Field(default_factory=list)
    planning_reference: str = ""
    decision_reference: str = ""
    confidence: float = Field(default=0.0, ge=0, le=1)


class MapleCognitiveContext(BaseModel):
    """认知上下文(聚合决策/对齐/记忆/失败智能)。"""

    decision_reference: str = ""
    human_alignment_reference: str = ""
    memory_reference: str = ""
    semantic_memory_reference: str = ""
    failure_reference: str = ""
    confidence: float = Field(default=0.0, ge=0, le=1)


class MapleCompanionContextReference(BaseModel):
    """统一只读认知快照(不是 Action / Executor 命令)。"""

    player_context: MaplePlayerContext | None = None
    world_context: MapleWorldContext | None = None
    goal_context: MapleGoalContext | None = None
    cognitive_context: MapleCognitiveContext | None = None
    summary: str = ""
    confidence: float = Field(default=0.0, ge=0, le=1)
    trace_id: str = ""
