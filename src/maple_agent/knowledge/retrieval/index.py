"""AliasIndex:exact / alias / prefix / fuzzy 匹配(优先级 Exact > Alias > Prefix > Fuzzy)。"""

from __future__ import annotations

import difflib
from typing import Protocol, runtime_checkable

from maple_agent.knowledge.retrieval.models import CandidateEntity


@runtime_checkable
class RetrievalStrategy(Protocol):
    """检索策略接口:未来可替换 Trie / BKTree / Embedding,保持结果兼容。"""

    def search(
        self,
        query: str,
        *,
        entity_type: str | None = None,
    ) -> list[CandidateEntity]: ...


class AliasIndex:
    """按实体 id/name/alias 建立索引,返回按可信度排序的候选。"""

    def __init__(self) -> None:
        self.index_version = "v1"
        self._entities: dict[tuple[str, str], CandidateEntity] = {}
        self._names: dict[str, CandidateEntity] = {}
        self._aliases: dict[str, CandidateEntity] = {}

    @classmethod
    def from_graph(cls, graph) -> AliasIndex:
        index = cls()
        for entity_type, nodes in (
            ("map", graph.maps),
            ("npc", graph.npcs),
            ("monster", graph.monsters),
            ("item", graph.items),
        ):
            for node in nodes:
                if entity_type == "map":
                    entity_id = node.map_id
                elif entity_type == "npc":
                    entity_id = node.npc_id
                elif entity_type == "monster":
                    entity_id = node.monster_id
                else:
                    entity_id = node.item_id
                entity = CandidateEntity(
                    entity_id=entity_id,
                    entity_type=entity_type,
                    text=node.name,
                )
                index._entities[(entity_type, str(entity_id))] = entity
                index._names[node.name] = entity
                for alias in node.aliases:
                    index._aliases[alias] = entity.model_copy(
                        update={"source": "alias"}
                    )
        return index

    def all(self) -> list[CandidateEntity]:
        return list(self._entities.values())

    def search(
        self,
        query: str,
        *,
        entity_type: str | None = None,
    ) -> list[CandidateEntity]:
        """返回按分数降序的候选(去重,保留最优来源)。"""
        results: dict[tuple[str, str], CandidateEntity] = {}

        def accept(candidate: CandidateEntity) -> bool:
            return entity_type is None or candidate.entity_type == entity_type

        def key(candidate: CandidateEntity) -> tuple[str, str]:
            return (candidate.entity_type, str(candidate.entity_id))

        for candidate in self._entities.values():
            if str(candidate.entity_id) == query and accept(candidate):
                results[key(candidate)] = candidate.model_copy(
                    update={
                        "score": 1.0,
                        "source": "exact",
                        "reason": "exact id",
                    }
                )

        candidate = self._names.get(query)
        if candidate is not None and accept(candidate):
            results[key(candidate)] = candidate.model_copy(
                update={
                    "score": 1.0,
                    "source": "exact",
                    "reason": "exact name",
                }
            )

        candidate = self._aliases.get(query)
        if candidate is not None and accept(candidate):
            results[key(candidate)] = candidate.model_copy(
                update={"score": 0.95, "reason": "alias"}
            )

        if len(query) >= 2:
            for name, candidate in list(self._names.items()) + list(
                self._aliases.items()
            ):
                if name.startswith(query) and accept(candidate):
                    results.setdefault(
                        key(candidate),
                        candidate.model_copy(
                            update={
                                "score": 0.8,
                                "source": "prefix",
                                "reason": "prefix",
                            }
                        ),
                    )

        for match in difflib.get_close_matches(query, list(self._names), n=3, cutoff=0.6):
            candidate = self._names[match]
            if accept(candidate):
                similarity = difflib.SequenceMatcher(None, query, match).ratio()
                results.setdefault(
                    key(candidate),
                    candidate.model_copy(
                        update={
                            "score": round(similarity * 0.7, 4),
                            "source": "fuzzy",
                            "reason": f"fuzzy {similarity:.2f}",
                        }
                    ),
                )
        return sorted(results.values(), key=lambda item: item.score, reverse=True)
