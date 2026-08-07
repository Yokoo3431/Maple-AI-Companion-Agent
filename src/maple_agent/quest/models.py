"""任务领域模型(Phase 2-A)。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class QuestObjective(BaseModel):
    """任务目标(如击杀/收集/对话/送达)。"""

    objective_id: str
    description: str = ""
    kind: str = "kill"
    target: str = ""
    quantity: int = Field(default=1, ge=1)
    completed: bool = False


class QuestRequirement(BaseModel):
    """任务接取条件(等级/物品/前置/位置)。"""

    kind: str = "level"
    target: str = ""
    quantity: int = Field(default=1, ge=1)


class QuestReward(BaseModel):
    """任务奖励(经验/金币/物品)。"""

    kind: str = "exp"
    target: str = ""
    quantity: int = Field(default=1, ge=1)


class Quest(BaseModel):
    """任务定义(含前置/关联 NPC/地图/怪物/物品)。"""

    quest_id: int | str
    name: str
    description: str = ""
    npc_id: int | str | None = None
    map_id: int | str | None = None
    monster_ids: list[int | str] = Field(default_factory=list)
    item_ids: list[int | str] = Field(default_factory=list)
    prerequisites: list[int | str] = Field(default_factory=list)
    requirements: list[QuestRequirement] = Field(default_factory=list)
    objectives: list[QuestObjective] = Field(default_factory=list)
    rewards: list[QuestReward] = Field(default_factory=list)
    version: str = ""


class QuestChain(BaseModel):
    """任务链(连续任务序列)。"""

    chain_id: str
    name: str = ""
    quest_ids: list[int | str] = Field(default_factory=list)
