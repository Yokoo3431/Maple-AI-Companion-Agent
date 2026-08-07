"""FusionService:OCR Text → Alias Matching → Knowledge Graph → WorldState。"""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from maple_agent.fusion.models import WorldState
from maple_agent.knowledge.models import MapInfo, MonsterInfo, NpcInfo
from maple_agent.knowledge.retrieval import AliasIndex, EntityRanker, RankingResult
from maple_agent.knowledge_graph.graph import KnowledgeGraph
from maple_agent.logging_setup import TraceContext
from maple_agent.providers.knowledge import KnowledgeProvider
from maple_agent.vision.models import Observation

logger = logging.getLogger("maple_agent.fusion")


class FusionService:
    """把 Vision 的 Observation 与知识(图谱)关联,生成 WorldState。"""

    def __init__(
        self,
        knowledge: KnowledgeProvider,
        *,
        graph: KnowledgeGraph | None = None,
        sessions_dir: str | Path = "sessions",
    ) -> None:
        self.knowledge = knowledge
        self.graph = graph
        self.sessions_dir = Path(sessions_dir)
        self._index = AliasIndex.from_graph(graph) if graph is not None else None
        self.ranker = EntityRanker()
        self._last_match: dict | None = None

    def fuse(
        self,
        observations: list[Observation],
        *,
        trace_id: str | None = None,
    ) -> WorldState:
        with TraceContext(trace_id=trace_id) as trace:
            map_name, map_confidence, matched_text = self._resolve_map(
                observations, trace.trace_id
            )
            current_map = (
                self.knowledge.get_map(map_name, trace_id=trace.trace_id)
                if map_name
                else None
            )
            npcs, monsters = self._entities(
                current_map, observations, trace.trace_id
            )
            world = WorldState(
                current_map=current_map,
                known_npcs=npcs,
                known_monsters=monsters,
                confidence=round(map_confidence, 4),
                trace_id=trace.trace_id,
            )
            if self.graph is not None and map_name is not None:
                self._write_knowledge_match(
                    trace.trace_id,
                    matched_text,
                    map_name,
                    map_confidence,
                )
            logger.info(
                "fusion complete: map=%s confidence=%s npcs=%d monsters=%d",
                current_map.name if current_map else None,
                world.confidence,
                len(npcs),
                len(monsters),
            )
            return world

    def _resolve_map(
        self,
        observations: list[Observation],
        tid: str,
    ) -> tuple[str | None, float, str]:
        """优先取 map_name 元素;否则文本经图谱/知识库别名解析。"""
        for obs in observations:
            if obs.element == "map_name" and isinstance(obs.normalized_value, str):
                return obs.normalized_value, obs.confidence, obs.normalized_value
        for obs in observations:
            if obs.type == "text" and obs.normalized_value:
                text = str(obs.normalized_value)
                if self.graph is not None:
                    best_map: RankingResult | None = None
                    best_fuzzy: RankingResult | None = None
                    for candidate_text, boost in self._candidates(text):
                        ranking = self._rank_entity(
                            candidate_text,
                            entity_type="map",
                            ocr_confidence=obs.confidence,
                            boost=boost,
                        )
                        if ranking.best is not None:
                            if ranking.best.source != "fuzzy" and best_map is None:
                                best_map = ranking
                            if best_fuzzy is None or (
                                ranking.best.score > best_fuzzy.best.score
                            ):
                                best_fuzzy = ranking
                    chosen = best_map or best_fuzzy
                    if chosen is not None:
                        candidate_list = self._candidates(text)
                        node = self.graph.find_map(chosen.best.entity_id)
                        if node is not None:
                            self._last_match = {
                                "ocr_text": text,
                                "candidate_list": [
                                    {"text": item, "score": s}
                                    for item, s in candidate_list
                                ],
                                "ranking": [
                                    item
                                    for item, _ in candidate_list
                                    if self._index.search(
                                        item, entity_type="map"
                                    )
                                ],
                                "matched": chosen.best.text,
                                "confidence": chosen.best.score,
                                "dataset_version": self.knowledge.dataset_version(),
                                "candidate_scores": [
                                    candidate.model_dump()
                                    for candidate in chosen.candidates
                                ],
                                "ranking_reason": chosen.ranking_reason,
                            }
                            return (
                                node.name,
                                chosen.best.score,
                                text,
                            )
                else:
                    resolved = self.knowledge.resolve_alias(text, trace_id=tid)
                    if resolved:
                        return resolved, obs.confidence, text
        return None, 0.0, ""

    @staticmethod
    def _candidates(text: str) -> list[tuple[str, float]]:
        """OCR 纠错候选:原文(1.0)、去尾部数字/符号(0.9)、全去数字/符号(0.8)。"""
        cleaned = re.sub(r"[\d\W_]+$", "", text)
        cleaned_all = re.sub(r"[\d\W_]+", "", text)
        result: list[tuple[str, float]] = [(text, 1.0)]
        if cleaned and cleaned != text:
            result.append((cleaned, 0.9))
        if (
            cleaned_all
            and cleaned_all != text
            and cleaned_all != cleaned
        ):
            result.append((cleaned_all, 0.8))
        return result

    def _rank_entity(
        self,
        query: str,
        *,
        entity_type: str,
        ocr_confidence: float,
        boost: float = 1.0,
        context_hits: set[str] | None = None,
    ) -> RankingResult:
        if self._index is None:
            return RankingResult(query=query, ocr_confidence=ocr_confidence)
        candidates = self._index.search(query, entity_type=entity_type)
        result = self.ranker.rank(
            query,
            candidates,
            ocr_confidence=ocr_confidence,
            context_hits=context_hits,
        )
        if result.best is not None and boost != 1.0:
            result = result.model_copy(
                update={
                    "best": result.best.model_copy(
                        update={"score": round(result.best.score * boost, 4)}
                    )
                }
            )
        return result

    def _entities(
        self,
        current_map: MapInfo | None,
        observations: list[Observation],
        tid: str,
    ) -> tuple[list[NpcInfo], list[MonsterInfo]]:
        npcs: list[NpcInfo] = []
        monsters: list[MonsterInfo] = []
        if current_map is not None:
            if self.graph is not None:
                for node in self.graph.npcs_in_map(current_map.map_id):
                    entity = self.knowledge.get_npc(node.npc_id, trace_id=tid)
                    if entity is not None and entity.npc_id not in {
                        item.npc_id for item in npcs
                    }:
                        npcs.append(entity)
                for node in self.graph.monsters_in_map(current_map.map_id):
                    entity = self.knowledge.get_monster(node.monster_id, trace_id=tid)
                    if entity is not None and entity.monster_id not in {
                        item.monster_id for item in monsters
                    }:
                        monsters.append(entity)
            else:
                npcs = self.knowledge.get_npcs_by_map(current_map.map_id, trace_id=tid)
                monsters = self.knowledge.get_monsters_by_map(
                    current_map.map_id, trace_id=tid
                )
        if self.graph is not None:
            for obs in observations:
                if obs.type != "text" or not obs.normalized_value:
                    continue
                text = str(obs.normalized_value)
                npc_ranking = self._rank_entity(
                    text, entity_type="npc", ocr_confidence=obs.confidence
                )
                if npc_ranking.best is not None:
                    entity = self.knowledge.get_npc(
                        npc_ranking.best.entity_id, trace_id=tid
                    )
                    if entity is not None and entity.npc_id not in {
                        item.npc_id for item in npcs
                    }:
                        npcs.append(entity)
                monster_ranking = self._rank_entity(
                    text, entity_type="monster", ocr_confidence=obs.confidence
                )
                if monster_ranking.best is not None:
                    entity = self.knowledge.get_monster(
                        monster_ranking.best.entity_id, trace_id=tid
                    )
                    if entity is not None and entity.monster_id not in {
                        item.monster_id for item in monsters
                    }:
                        monsters.append(entity)
        return npcs, monsters

    def _write_knowledge_match(
        self,
        trace_id: str,
        ocr_text: str,
        matched: str,
        confidence: float,
    ) -> None:
        directory = self.sessions_dir / trace_id
        directory.mkdir(parents=True, exist_ok=True)
        payload = {
            "trace_id": trace_id,
            "ocr_text": ocr_text,
            "candidate": ocr_text,
            "matched": matched,
            "confidence": confidence,
            "dataset_version": (
                self._last_match.get("dataset_version")
                if self._last_match
                else self.knowledge.dataset_version()
            ),
            "candidate_list": (
                self._last_match.get("candidate_list")
                if self._last_match
                else [{"text": ocr_text, "score": 1.0}]
            ),
            "ranking": (
                self._last_match.get("ranking")
                if self._last_match
                else [matched]
            ),
            "candidate_scores": (
                self._last_match.get("candidate_scores")
                if self._last_match
                else []
            ),
            "ranking_reason": (
                self._last_match.get("ranking_reason")
                if self._last_match
                else ""
            ),
            "evaluation_context": {
                "index_version": (
                    self._index.index_version if self._index is not None else "v1"
                ),
                "dataset_version": (
                    self._last_match.get("dataset_version")
                    if self._last_match
                    else self.knowledge.dataset_version()
                ),
                "retrieval_strategy": "exact_alias_prefix_fuzzy",
                "candidate_count": (
                    len(self._last_match.get("candidate_scores", []))
                    if self._last_match
                    else 0
                ),
            },
        }
        (directory / "knowledge_match.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def map_for(
        self,
        map_name: str,
        *,
        trace_id: str | None = None,
    ) -> MapInfo | None:
        """按名称(含别名)直接查地图。"""
        return self.knowledge.get_map(map_name, trace_id=trace_id)
