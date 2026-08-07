"""Decision Intelligence 领域模型(Phase 5-A,只做决策建模,不触发执行)。"""

from __future__ import annotations

from pydantic import BaseModel, Field

from maple_agent.context.models import KnowledgeState
from maple_agent.fusion.models import WorldState
from maple_agent.goal.models import Goal
from maple_agent.quest_planner.models import QuestPlan


class DecisionOption(BaseModel):
    """候选决策选项(语义动作,非物理输入)。"""

    decision_id: str
    action: str
    target: str = ""
    expected_result: str = ""
    confidence: float = Field(default=0.0, ge=0, le=1)
    risk: float = Field(default=0.0, ge=0, le=1)
    reason: str = ""


class DecisionContext(BaseModel):
    """决策输入上下文(只读快照)。"""

    world_state: WorldState | None = None
    knowledge_state: KnowledgeState | None = None
    goal: Goal | None = None
    quest_plan: QuestPlan | None = None
    options: list[DecisionOption] = Field(default_factory=list)


class DecisionResult(BaseModel):
    """决策结果(仅推荐,不触发执行)。"""

    selected_option: DecisionOption | None = None
    alternatives: list[DecisionOption] = Field(default_factory=list)
    rejected: list[DecisionOption] = Field(default_factory=list)
    score: float = Field(default=0.0, ge=0, le=1)
    explanation: str = ""
    trace_id: str = ""
