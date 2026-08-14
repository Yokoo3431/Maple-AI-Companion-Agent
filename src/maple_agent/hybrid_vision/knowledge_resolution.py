"""KnowledgeGuidedResolver:Knowledge=PRIOR/RESOLUTION,绝不伪造观察。"""

from __future__ import annotations

from maple_agent.hybrid_vision.models import (
    EvidenceResolution,
    PerceptionEvidence,
    ResolutionCandidate,
    ResolutionMatchType,
    ResolutionResult,
)


def _normalize(value: str) -> str:
    return "".join(value.lower().split())


class KnowledgeGuidedResolver:
    """在 Knowledge 候选集合内解析视觉证据为 canonical ID。

    核心不变量:
    expected(Knowledge 先验) != observed(视觉证据);
    Knowledge 说地图里有 npc_a 不等于视觉看到了 npc_a。
    """

    def __init__(
        self,
        *,
        knowledge=None,
        alias_index=None,
        min_evidence_confidence: float = 0.30,
    ) -> None:
        self.knowledge = knowledge
        self.alias_index = alias_index
        self.min_evidence_confidence = min_evidence_confidence

    def resolve_name(
        self,
        observed_name: str,
        *,
        evidence_confidence: float = 0.0,
        candidates: list[dict] | None = None,
        knowledge_type: str | None = None,
    ) -> ResolutionResult:
        """把视觉观察名称解析为 canonical 候选。

        candidates: [{"id":..., "name":..., "aliases":[...]}]
        无观察 / 低置信度 / 不在候选集合 -> 一律 unresolved(不伪造)。
        """
        observed = (observed_name or "").strip()
        if not observed:
            return ResolutionResult(
                resolved=False,
                reasoning=[
                    "no visual evidence; knowledge prior does not "
                    "create observation"
                ],
            )
        if evidence_confidence < self.min_evidence_confidence:
            return ResolutionResult(
                resolved=False,
                confidence=evidence_confidence,
                reasoning=[
                    "visual evidence confidence below threshold; "
                    "not resolved"
                ],
            )
        candidates = self._candidate_pool(
            candidates, knowledge_type=knowledge_type
        )
        observed_norm = _normalize(observed)
        best: dict | None = None
        best_score = 0.0
        for candidate in candidates:
            names = [candidate.get("name", "")]
            names.extend(candidate.get("aliases", []) or [])
            names.append(candidate.get("id", ""))
            for name in names:
                if not name:
                    continue
                norm = _normalize(str(name))
                if norm == observed_norm:
                    best = candidate
                    best_score = 1.0
                    break
                if norm and (
                    norm in observed_norm or observed_norm in norm
                ):
                    score = min(
                        1.0,
                        len(norm) / max(1, len(observed_norm)),
                    )
                    if score > best_score:
                        best = candidate
                        best_score = score
            if best_score >= 1.0:
                break
        if best is None:
            return ResolutionResult(
                resolved=False,
                confidence=evidence_confidence,
                reasoning=[
                    f"observed {observed!r} not in candidate set; "
                    "expected != observed"
                ],
            )
        confidence = round(evidence_confidence * best_score, 4)
        return ResolutionResult(
            resolved=True,
            canonical_candidate_id=str(best.get("id", "")),
            display_name=str(best.get("name", observed)),
            confidence=confidence,
            source="knowledge-resolution",
            reasoning=[
                f"observed {observed!r} resolved to "
                f"{best.get('id', '')} ({best.get('name', '')})"
            ],
        )

    def candidates_for_map(
        self,
        map_id_or_name: str,
    ) -> list[dict]:
        """Knowledge 先验:某地图可能的 NPC/Monster/Item(仅候选,非观察)。"""
        if self.knowledge is None:
            return []
        anchor = self.knowledge.find_by_name(map_id_or_name)
        if anchor is None:
            anchor = self.knowledge.base.get_entity(map_id_or_name)
        if anchor is None:
            return []
        results: list[dict] = []
        for relation, target in self.knowledge.find_related(
            anchor.knowledge_id
        ):
            relation_type = getattr(relation, "relation_type", "")
            relation_name = (
                relation_type.value
                if hasattr(relation_type, "value")
                else str(relation_type)
            )
            if "CONTAINS" in relation_name or "SPAWNS" in relation_name:
                results.append(
                    {
                        "id": target.knowledge_id,
                        "name": target.name,
                        "knowledge_type": (
                            target.knowledge_type.value
                            if hasattr(target.knowledge_type, "value")
                            else str(target.knowledge_type)
                        ),
                    }
                )
        return results

    def _candidate_pool(
        self,
        candidates: list[dict] | None,
        *,
        knowledge_type: str | None,
    ) -> list[dict]:
        if candidates is not None:
            return candidates
        if self.knowledge is None:
            return []
        pool = []
        for entity in self.knowledge.all_entities():
            if knowledge_type and entity.knowledge_type.value != knowledge_type:
                continue
            pool.append(
                {
                    "id": entity.knowledge_id,
                    "name": entity.name,
                    "aliases": getattr(entity, "aliases", None) or [],
                }
            )
        return pool

    @staticmethod
    def observation_probe(
        *,
        evidence_value: str,
        candidates: list[dict],
        evidence_confidence: float = 0.9,
        resolver: KnowledgeGuidedResolver | None = None,
    ) -> ResolutionResult:
        """独立探针:明确把视觉证据与 Knowledge 候选分离。"""
        resolver = resolver or KnowledgeGuidedResolver()
        return resolver.resolve_name(
            evidence_value,
            evidence_confidence=evidence_confidence,
            candidates=candidates,
        )


class EvidenceResolver:
    """Resolve PerceptionEvidence deterministically against a canonical graph."""

    _MATCH_SCORES = {
        ResolutionMatchType.EXACT_ID: 1.0,
        ResolutionMatchType.EXACT_NAME: 1.0,
        ResolutionMatchType.ALIAS: 0.95,
    }

    def resolve(
        self,
        evidence: PerceptionEvidence,
        graph,
        *,
        knowledge_type: str | None = None,
    ) -> EvidenceResolution:
        observed = str(evidence.value if evidence.value is not None else evidence.raw_value)
        normalized = _normalize(observed)
        result = EvidenceResolution(
            evidence_id=evidence.evidence_id,
            observed_value=observed,
            evidence_confidence=evidence.confidence,
        )
        if not normalized:
            result.reasoning.append("empty observed value; unresolved")
            return result

        candidates: list[ResolutionCandidate] = []
        for entity in graph.all_entities():
            entity_type = entity.knowledge_type.value
            if knowledge_type and entity_type != knowledge_type:
                continue
            match_type = self._match(entity, normalized)
            if match_type is None:
                continue
            match_score = self._MATCH_SCORES[match_type]
            candidates.append(
                ResolutionCandidate(
                    evidence_id=evidence.evidence_id,
                    canonical_id=entity.knowledge_id,
                    entity_type=entity_type,
                    display_name=entity.name,
                    match_type=match_type,
                    match_score=match_score,
                    resolution_confidence=round(
                        evidence.confidence * match_score, 4
                    ),
                    source=entity.provenance.source_id or entity.source,
                    version=entity.version or entity.provenance.data_version,
                )
            )
        candidates.sort(
            key=lambda item: (
                -item.match_score,
                -item.resolution_confidence,
                item.canonical_id,
            )
        )
        result.candidates = candidates
        if not candidates:
            result.reasoning.append("observed value not found; unresolved")
            return result
        best_score = candidates[0].match_score
        top = [item for item in candidates if item.match_score == best_score]
        if len(top) > 1:
            result.conflict = True
            result.reasoning.append("multiple canonical candidates share the best match")
            return result
        result.selected = candidates[0]
        result.resolved = True
        result.reasoning.append(
            f"{candidates[0].match_type.value.lower()} match; evidence preserved"
        )
        return result

    @staticmethod
    def _match(entity, normalized: str) -> ResolutionMatchType | None:
        if _normalize(entity.knowledge_id) == normalized:
            return ResolutionMatchType.EXACT_ID
        if _normalize(entity.name) == normalized:
            return ResolutionMatchType.EXACT_NAME
        if any(_normalize(alias) == normalized for alias in entity.aliases):
            return ResolutionMatchType.ALIAS
        return None
