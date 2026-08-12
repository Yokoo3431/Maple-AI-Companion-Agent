"""CanonicalMapper:外部 ID/名称/别名 -> canonical Maple ID(确定性,禁止模糊合并)。"""

from __future__ import annotations

from maple_agent.knowledge_quality.models import (
    CanonicalEntityReference,
    MergeOutcome,
    MergeRecord,
)


def normalize_name(name: str) -> str:
    """统一空白与大小写(简繁映射表留作未来确定性扩展)。"""
    return " ".join(name.strip().lower().split())


class CanonicalMapper:
    """维护确定性 alias 表并解析外部引用。"""

    def __init__(
        self,
        canonical_entities: list[CanonicalEntityReference] | None = None,
    ) -> None:
        self._entities: dict[str, CanonicalEntityReference] = {}
        self._by_name: dict[str, str] = {}
        self.last_records: list[MergeRecord] = []
        for entity in canonical_entities or []:
            self.register(entity)

    @classmethod
    def from_maple_graph(
        cls,
        graph,
        *,
        game_profile: str = "",
        server_profile: str = "",
        data_version: str = "",
    ) -> CanonicalMapper:
        entities = [
            CanonicalEntityReference(
                canonical_id=entity.knowledge_id,
                entity_type=entity.knowledge_type.value,
                display_name=entity.name,
                aliases=list(entity.aliases),
                game_profile=game_profile,
                server_profile=server_profile,
                data_version=data_version,
            )
            for entity in graph.all_entities()
        ]
        return cls(entities)

    def register(self, entity: CanonicalEntityReference) -> None:
        self._entities[entity.canonical_id] = entity
        self._by_name[normalize_name(entity.display_name)] = (
            entity.canonical_id
        )
        for alias in entity.aliases:
            self._by_name[normalize_name(alias)] = entity.canonical_id

    def lookup(self, name: str) -> str | None:
        return self._by_name.get(normalize_name(name))

    def get(self, canonical_id: str) -> CanonicalEntityReference | None:
        return self._entities.get(canonical_id)

    def resolve(
        self,
        *,
        external_id: str = "",
        canonical_id: str = "",
        name: str = "",
        aliases: list[str] | None = None,
        source_id_mapping: dict[str, str] | None = None,
    ) -> tuple[str, MergeOutcome, str]:
        """确定性映射:canonical_id > source mapping > 规范化名称 > aliases > UNRESOLVED。"""
        if canonical_id and canonical_id in self._entities:
            return canonical_id, MergeOutcome.MERGED, "exact canonical id"
        if canonical_id:
            # 提供 canonical_id 但未知 -> 不猜测
            return "", MergeOutcome.UNRESOLVED, "unknown canonical id"
        if external_id and source_id_mapping:
            mapped = source_id_mapping.get(external_id)
            if mapped and mapped in self._entities:
                return mapped, MergeOutcome.MERGED, "external source id mapping"
        for candidate in [name, *(aliases or [])]:
            if not candidate:
                continue
            matched = self.lookup(candidate)
            if matched:
                return matched, MergeOutcome.MERGED, f"name/alias match: {candidate}"
        return "", MergeOutcome.UNRESOLVED, "no deterministic mapping"

    def record(
        self,
        *,
        external_id: str,
        canonical_id: str,
        outcome: MergeOutcome,
        reason: str,
        evidence: dict | None = None,
    ) -> MergeRecord:
        record = MergeRecord(
            external_id=external_id,
            canonical_id=canonical_id,
            outcome=outcome,
            reason=reason,
            evidence=evidence or {},
        )
        self.last_records.append(record)
        return record

    def summary(self) -> dict:
        counts: dict[str, int] = {}
        for record in self.last_records:
            counts[record.outcome.value] = counts.get(record.outcome.value, 0) + 1
        return counts
