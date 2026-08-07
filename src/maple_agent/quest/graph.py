"""Quest Graph:前置/NPC/地图/怪物/物品关联查询。"""

from __future__ import annotations

from collections import defaultdict

from maple_agent.quest.models import Quest


class QuestGraph:
    """基于任务列表构建的关联图(只读查询)。"""

    def __init__(self, quests: list[Quest]) -> None:
        self._quests: dict[str, Quest] = {}
        self._by_npc: dict[str, list[Quest]] = defaultdict(list)
        self._by_map: dict[str, list[Quest]] = defaultdict(list)
        self._by_monster: dict[str, list[Quest]] = defaultdict(list)
        self._by_item: dict[str, list[Quest]] = defaultdict(list)
        for quest in quests:
            self._quests[str(quest.quest_id)] = quest
            if quest.npc_id is not None:
                self._by_npc[str(quest.npc_id)].append(quest)
            if quest.map_id is not None:
                self._by_map[str(quest.map_id)].append(quest)
            for monster_id in quest.monster_ids:
                self._by_monster[str(monster_id)].append(quest)
            for item_id in quest.item_ids:
                self._by_item[str(item_id)].append(quest)

    @property
    def quests(self) -> list[Quest]:
        return list(self._quests.values())

    def get(self, quest_id: int | str) -> Quest | None:
        return self._quests.get(str(quest_id))

    def prerequisites_of(self, quest_id: int | str) -> list[Quest]:
        quest = self.get(quest_id)
        if quest is None:
            return []
        return [
            item
            for prerequisite in quest.prerequisites
            if (item := self._quests.get(str(prerequisite))) is not None
        ]

    def by_npc(self, npc_id: int | str) -> list[Quest]:
        return list(self._by_npc.get(str(npc_id), []))

    def by_map(self, map_id: int | str) -> list[Quest]:
        return list(self._by_map.get(str(map_id), []))

    def by_monster(self, monster_id: int | str) -> list[Quest]:
        return list(self._by_monster.get(str(monster_id), []))

    def by_item(self, item_id: int | str) -> list[Quest]:
        return list(self._by_item.get(str(item_id), []))

    def available(
        self,
        completed_ids: list[int | str] | None = None,
    ) -> list[Quest]:
        """返回前置全部满足(或无前置)的任务。"""
        completed = {str(item) for item in (completed_ids or [])}
        return [
            quest
            for quest in self._quests.values()
            if all(str(prereq) in completed for prereq in quest.prerequisites)
        ]
