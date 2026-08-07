"""Knowledge Provider:地图/NPC/怪物/任务知识查询(Phase 1.3,只读)。"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from maple_agent.events import EventBus
from maple_agent.knowledge.dataset import KnowledgeDataset, load_dataset
from maple_agent.knowledge.loader import KnowledgeData, detect_profile, load_profile
from maple_agent.knowledge.models import (
    MapDictionary,
    MapInfo,
    MonsterInfo,
    NpcInfo,
    QuestTemplate,
)
from maple_agent.providers.base import BaseProvider
from maple_agent.quest.graph import QuestGraph
from maple_agent.quest.models import Quest, QuestObjective, QuestRequirement, QuestReward

logger = logging.getLogger("maple_agent.knowledge")


class KnowledgeProvider(BaseProvider):
    """知识库 Provider 抽象(复用 BaseProvider 生命周期)。"""

    def __init__(self, *, bus: EventBus | None = None, source: str = "knowledge") -> None:
        super().__init__(name=source, logger_name="maple_agent.knowledge", bus=bus)
        self._configured_profile = ""
        self._profile_available = False
        self._data = KnowledgeData()
        self._quest_graph = QuestGraph([])
        self._dataset: KnowledgeDataset | None = None
        self._dataset_dir = (
            Path(__file__).resolve().parents[1] / "knowledge" / "data"
        )

    @property
    def dataset(self) -> KnowledgeDataset | None:
        return self._dataset

    def load_dataset(
        self, directory: str | Path | None = None
    ) -> KnowledgeDataset:
        """启动时加载 JSON 数据集(失败安全降级)。"""
        self._dataset = load_dataset(directory or self._dataset_dir)
        return self._dataset

    def reload(self, *, trace_id: str | None = None) -> None:
        """重新加载数据集(profile 数据由子类覆盖处理)。"""
        self._dataset = None
        self.load_dataset()

    def dataset_version(self) -> str:
        return self._dataset.version if self._dataset is not None else ""

    @property
    def data(self) -> KnowledgeData:
        return self._data

    @property
    def game_profile(self) -> str:
        return self._data.game_profile

    @property
    def version(self) -> str:
        return self._data.version

    @property
    def counts(self) -> dict[str, int]:
        return self._data.counts

    @property
    def profile_status(self) -> str:
        if not self._data.game_profile:
            return "unconfigured"
        return "ok" if self._profile_available else "missing"

    def load_map_dictionary(self, *, trace_id: str | None = None) -> MapDictionary:
        return self._lookup("load_map_dictionary", lambda: self._data.to_dictionary(), trace_id)

    def resolve_alias(self, name: str, *, trace_id: str | None = None) -> str | None:
        def _resolve() -> str | None:
            for map_name, aliases in self._data.to_dictionary().entries.items():
                if name == map_name or name in aliases:
                    return map_name
            return None

        return self._lookup("resolve_alias", _resolve, trace_id)

    def get_map(
        self, ref: int | str, *, trace_id: str | None = None
    ) -> MapInfo | None:
        result = self._lookup(
            "get_map",
            lambda: self._find(self._data.maps, "map_id", ref),
            trace_id,
        )
        if result is None:
            node = self._dataset_map(ref)
            if node is not None:
                result = MapInfo(
                    map_id=node.map_id,
                    name=node.name,
                    aliases=node.aliases,
                    region=node.region,
                    version=self.dataset_version(),
                )
        return result

    def get_npc(
        self, ref: int | str, *, trace_id: str | None = None
    ) -> NpcInfo | None:
        result = self._lookup(
            "get_npc",
            lambda: self._find(self._data.npcs, "npc_id", ref),
            trace_id,
        )
        if result is None:
            node = self._dataset_npc(ref)
            if node is not None:
                result = NpcInfo(
                    npc_id=node.npc_id,
                    name=node.name,
                    aliases=node.aliases,
                    map_id=node.location,
                    version=self.dataset_version(),
                )
        return result

    def get_monster(
        self, ref: int | str, *, trace_id: str | None = None
    ) -> MonsterInfo | None:
        result = self._lookup(
            "get_monster",
            lambda: self._find(self._data.monsters, "monster_id", ref),
            trace_id,
        )
        if result is None:
            node = self._dataset_monster(ref)
            if node is not None:
                result = MonsterInfo(
                    monster_id=node.monster_id,
                    name=node.name,
                    level=node.level,
                    map_id=node.location,
                    version=self.dataset_version(),
                )
        return result

    def get_npcs_by_map(
        self, map_id: int | str, *, trace_id: str | None = None
    ) -> list[NpcInfo]:
        result = self._lookup(
            "get_npcs_by_map",
            lambda: [item for item in self._data.npcs if str(item.map_id) == str(map_id)],
            trace_id,
        )
        if not result and self._dataset is not None:
            result = [
                NpcInfo(
                    npc_id=node.npc_id,
                    name=node.name,
                    aliases=node.aliases,
                    map_id=node.location,
                    version=self.dataset_version(),
                )
                for node in self._dataset.npcs
                if str(node.location) == str(map_id)
            ]
        return result

    def get_monsters_by_map(
        self, map_id: int | str, *, trace_id: str | None = None
    ) -> list[MonsterInfo]:
        result = self._lookup(
            "get_monsters_by_map",
            lambda: [
                item for item in self._data.monsters if str(item.map_id) == str(map_id)
            ],
            trace_id,
        )
        if not result and self._dataset is not None:
            result = [
                MonsterInfo(
                    monster_id=node.monster_id,
                    name=node.name,
                    level=node.level,
                    map_id=node.location,
                    version=self.dataset_version(),
                )
                for node in self._dataset.monsters
                if str(node.location) == str(map_id)
            ]
        return result

    def _dataset_map(self, ref: int | str):
        if self._dataset is None:
            return None
        key = str(ref)
        for node in self._dataset.maps:
            if str(node.map_id) == key or node.name == ref or ref in node.aliases:
                return node
        return None

    def _dataset_npc(self, ref: int | str):
        if self._dataset is None:
            return None
        key = str(ref)
        for node in self._dataset.npcs:
            if str(node.npc_id) == key or node.name == ref or ref in node.aliases:
                return node
        return None

    def _dataset_monster(self, ref: int | str):
        if self._dataset is None:
            return None
        key = str(ref)
        for node in self._dataset.monsters:
            if str(node.monster_id) == key or node.name == ref or ref in node.aliases:
                return node
        return None

    def get_quest_template(
        self, ref: int | str, *, trace_id: str | None = None
    ) -> QuestTemplate | None:
        return self._lookup(
            "get_quest_template",
            lambda: self._find(self._data.quests, "quest_id", ref),
            trace_id,
        )

    def get_quest(
        self, ref: int | str, *, trace_id: str | None = None
    ) -> Quest | None:
        return self._lookup(
            "get_quest",
            lambda: self._quest_graph.get(ref),
            trace_id,
        )

    def get_available_quests(
        self,
        completed_ids: list[int | str] | None = None,
        *,
        trace_id: str | None = None,
    ) -> list[Quest]:
        return self._lookup(
            "get_available_quests",
            lambda: self._quest_graph.available(completed_ids),
            trace_id,
        )

    def _find(self, items: list[Any], id_field: str, ref: int | str) -> Any | None:
        key = str(ref)
        for item in items:
            if str(getattr(item, id_field)) == key or item.name == ref:
                return item
        return None

    def _lookup(self, operation: str, fn, trace_id: str | None) -> Any:
        self._require_initialized()
        with self._trace(trace_id):
            logger.info("knowledge lookup: %s", operation)
            return fn()


class JsonKnowledgeProvider(KnowledgeProvider):
    """从 knowledge/versions/<game_profile>/ 加载 JSON/CSV 数据。"""

    def __init__(
        self,
        *,
        bus: EventBus | None = None,
        knowledge_root: str | Path = "knowledge",
        game_profile: str = "",
    ) -> None:
        super().__init__(bus=bus, source="json_knowledge")
        self.knowledge_root = Path(knowledge_root)
        self._configured_profile = game_profile

    def initialize(self, *, trace_id: str | None = None) -> None:
        super().initialize(trace_id=trace_id)
        self.load_dataset()
        with self._trace(trace_id):
            available, version = detect_profile(self.knowledge_root, self._configured_profile)
            if available:
                profile_dir = self.knowledge_root / "versions" / self._configured_profile
                self._data = load_profile(profile_dir, self._configured_profile)
                self._quest_graph = QuestGraph(self._data.quests_domain)
                self._profile_available = True
                logger.info(
                    "knowledge profile loaded: %s version=%s counts=%s",
                    self._configured_profile,
                    version,
                    self._data.counts,
                )
            else:
                self._data = KnowledgeData(
                    game_profile=self._configured_profile,
                    version=version,
                )
                self._quest_graph = QuestGraph([])
                self._profile_available = False
                logger.warning(
                    "knowledge profile missing: %s",
                    self._configured_profile or "(未配置)",
                )

    def reload(self, *, trace_id: str | None = None) -> None:
        """重新加载 profile 与 dataset。"""
        self._data = KnowledgeData()
        self._quest_graph = QuestGraph([])
        self._dataset = None
        with self._trace(trace_id):
            available, version = detect_profile(self.knowledge_root, self._configured_profile)
            if available:
                profile_dir = self.knowledge_root / "versions" / self._configured_profile
                self._data = load_profile(profile_dir, self._configured_profile)
                self._quest_graph = QuestGraph(self._data.quests_domain)
                self._profile_available = True
            else:
                self._data = KnowledgeData(
                    game_profile=self._configured_profile,
                    version=version,
                )
                self._quest_graph = QuestGraph([])
                self._profile_available = False
            self.load_dataset()


class MockKnowledgeProvider(KnowledgeProvider):
    """Mock 实现:固定示例数据(离线测试/演示用)。"""

    def __init__(self, *, bus: EventBus | None = None) -> None:
        super().__init__(bus=bus, source="mock_knowledge")
        self._configured_profile = "maple-v113"
        self._profile_available = True
        self._data = KnowledgeData(
            game_profile="maple-v113",
            version="v113",
            maps=[
                MapInfo(map_id=1, name="射手村", aliases=["Henesys"], region="冒险岛世界"),
                MapInfo(map_id=2, name="勇士部落", aliases=["Perion"], region="冒险岛世界"),
            ],
            npcs=[NpcInfo(npc_id=101, name="赫丽娜", map_id=1)],
            monsters=[
                MonsterInfo(monster_id=100, name="绿水灵", level=1, hp=15, map_id=1)
            ],
            quests=[
                QuestTemplate(
                    quest_id=1,
                    name="新手教学",
                    npc_id=101,
                    map_id=1,
                    requirements={"level": "1"},
                    rewards={"exp": "10"},
                )
            ],
            quests_domain=[
                Quest(
                    quest_id=1,
                    name="新手教学",
                    description="前往射手村找赫丽娜",
                    npc_id=101,
                    map_id=1,
                    monster_ids=[100],
                    item_ids=[1],
                    requirements=[QuestRequirement(kind="level", target="1", quantity=1)],
                    objectives=[
                        QuestObjective(
                            objective_id="o1",
                            description="与赫丽娜对话",
                            kind="talk",
                            target="101",
                        )
                    ],
                    rewards=[QuestReward(kind="exp", target="10", quantity=1)],
                ),
                Quest(
                    quest_id=2,
                    name="收集树液",
                    description="击杀绿水灵收集树液",
                    npc_id=101,
                    map_id=1,
                    monster_ids=[100],
                    item_ids=[2],
                    prerequisites=[1],
                    objectives=[
                        QuestObjective(
                            objective_id="o1",
                            description="收集 5 个树液",
                            kind="collect",
                            target="2",
                            quantity=5,
                        )
                    ],
                    rewards=[QuestReward(kind="meso", target="100", quantity=1)],
                ),
            ],
        )
        self._quest_graph = QuestGraph(self._data.quests_domain)
