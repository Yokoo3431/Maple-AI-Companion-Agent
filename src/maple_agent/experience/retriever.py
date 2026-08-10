"""ExperienceRetriever:当前世界/知识/目标 → 历史经验(只读)。"""

from __future__ import annotations

from maple_agent.context.models import KnowledgeState
from maple_agent.experience.models import ExperienceRecord
from maple_agent.experience.store import ExperienceStore
from maple_agent.fusion.models import WorldState
from maple_agent.goal.models import Goal


class ExperienceRetriever:
    """按当前情境检索历史经验,供决策加分。"""

    def __init__(self, store: ExperienceStore | None = None) -> None:
        self.store = store or ExperienceStore()
        self.last_query: dict = {}
        self.last_results: list[ExperienceRecord] = []

    def retrieve(
        self,
        *,
        world_state: WorldState | None = None,
        knowledge_state: KnowledgeState | None = None,
        goal: Goal | None = None,
        action: str = "",
        limit: int = 5,
    ) -> list[ExperienceRecord]:
        map_name = (
            world_state.current_map.name
            if world_state is not None and world_state.current_map is not None
            else ""
        )
        goal_text = goal.title if goal is not None else ""
        self.last_query = {
            "map_name": map_name,
            "goal": goal_text,
            "knowledge_confidence": (
                knowledge_state.confidence
                if knowledge_state is not None
                else 0.0
            ),
        }
        results = self.store.similar_situation(
            map_name=map_name,
            action=action,
            limit=limit,
        )
        self.last_results = results
        return results
