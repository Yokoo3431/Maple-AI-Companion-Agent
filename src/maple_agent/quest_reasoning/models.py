"""Maple Quest Intelligence 数据模型(Phase 9-F,任务/目标推理参考,只读)。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class QuestStateType(StrEnum):
    """任务状态(推理结论,非运行态)。"""

    UNKNOWN = "UNKNOWN"
    AVAILABLE = "AVAILABLE"
    ACCEPTED = "ACCEPTED"
    IN_PROGRESS = "IN_PROGRESS"
    REQUIREMENT_PENDING = "REQUIREMENT_PENDING"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"


class GoalType(StrEnum):
    """目标参考类型。"""

    QUEST_PROGRESS = "QUEST_PROGRESS"
    RESOURCE_PREPARATION = "RESOURCE_PREPARATION"
    NPC_INTERACTION_REFERENCE = "NPC_INTERACTION_REFERENCE"
    EXPLORATION_REFERENCE = "EXPLORATION_REFERENCE"
    KNOWLEDGE_QUERY = "KNOWLEDGE_QUERY"


class QuestReference(BaseModel):
    """领域知识任务引用。"""

    quest_id: str
    quest_name: str
    quest_type: str = ""
    description: str = ""
    requirements: list[str] = Field(default_factory=list)
    rewards: list[str] = Field(default_factory=list)
    related_entities: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0, le=1)


class QuestProgressReference(BaseModel):
    """任务进度参考(不是 Action)。"""

    quest_id: str
    quest_name: str = ""
    state: QuestStateType = QuestStateType.UNKNOWN
    completed_requirements: list[str] = Field(default_factory=list)
    pending_requirements: list[str] = Field(default_factory=list)
    progress_confidence: float = Field(default=0.0, ge=0, le=1)
    reasoning: list[str] = Field(default_factory=list)


class GoalReference(BaseModel):
    """目标参考(不是 Action / Executor 命令)。"""

    goal_id: str
    goal_type: GoalType
    description: str
    priority: float = Field(default=0.0, ge=0, le=1)
    related_quest: str = ""
    confidence: float = Field(default=0.0, ge=0, le=1)
    reasoning: str = ""


class GoalDependency(BaseModel):
    """目标依赖图边(仅图信息,不构成动作链)。"""

    dependency_id: str
    goal_id: str
    depends_on: str
    dependency_type: str = "REFERENCE"
    confidence: float = Field(default=0.0, ge=0, le=1)
    reasoning: str = ""


class QuestGoalReference(BaseModel):
    """任务智能最终输出(只读参考)。"""

    active_quests: list[QuestReference] = Field(default_factory=list)
    quest_progress: list[QuestProgressReference] = Field(
        default_factory=list
    )
    recommended_goals: list[GoalReference] = Field(default_factory=list)
    blocked_goals: list[GoalReference] = Field(default_factory=list)
    dependencies: list[GoalDependency] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0, le=1)
    reasoning: list[str] = Field(default_factory=list)
