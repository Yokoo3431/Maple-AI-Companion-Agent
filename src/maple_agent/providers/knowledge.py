"""Knowledge Provider:地图/NPC/怪物/任务知识查询(Phase 1.3,只读)。"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from maple_agent.events import EventBus
from maple_agent.knowledge.loader import KnowledgeData, detect_profile, load_profile
from maple_agent.knowledge.models import (
    MapDictionary,
    MapInfo,
    MonsterInfo,
    NpcInfo,
    QuestTemplate,
)
from maple_agent.providers.base import BaseProvider

logger = logging.getLogger("maple_agent.knowledge")


class KnowledgeProvider(BaseProvider):
    """知识库 Provider 抽象(复用 BaseProvider 生命周期)。"""

    def __init__(self, *, bus: EventBus | None = None, source: str = "knowledge") -> None:
        super().__init__(name=source, logger_name="maple_agent.knowledge", bus=bus)
        self._configured_profile = ""
        self._profile_available = False
        self._data = KnowledgeData()

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
        return self._lookup("get_map", lambda: self._find(self._data.maps, "map_id", ref), trace_id)

    def get_npc(
        self, ref: int | str, *, trace_id: str | None = None
    ) -> NpcInfo | None:
        return self._lookup("get_npc", lambda: self._find(self._data.npcs, "npc_id", ref), trace_id)

    def get_monster(
        self, ref: int | str, *, trace_id: str | None = None
    ) -> MonsterInfo | None:
        return self._lookup(
            "get_monster",
            lambda: self._find(self._data.monsters, "monster_id", ref),
            trace_id,
        )

    def get_quest_template(
        self, ref: int | str, *, trace_id: str | None = None
    ) -> QuestTemplate | None:
        return self._lookup(
            "get_quest_template",
            lambda: self._find(self._data.quests, "quest_id", ref),
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
        with self._trace(trace_id):
            available, version = detect_profile(self.knowledge_root, self._configured_profile)
            if available:
                profile_dir = self.knowledge_root / "versions" / self._configured_profile
                self._data = load_profile(profile_dir, self._configured_profile)
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
                self._profile_available = False
                logger.warning(
                    "knowledge profile missing: %s",
                    self._configured_profile or "(未配置)",
                )


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
            monsters=[MonsterInfo(monster_id=100, name="绿水灵", level=1, hp=15)],
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
        )
