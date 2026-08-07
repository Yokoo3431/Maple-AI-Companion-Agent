"""FusionService:OCR Text → Alias Matching → Knowledge Graph → WorldState。"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from maple_agent.fusion.models import WorldState
from maple_agent.knowledge.models import MapInfo, MonsterInfo, NpcInfo
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
                    node = self.graph.find_map(text)
                    if node is not None:
                        return node.name, obs.confidence, text
                else:
                    resolved = self.knowledge.resolve_alias(text, trace_id=tid)
                    if resolved:
                        return resolved, obs.confidence, text
        return None, 0.0, ""

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
                npc_node = self.graph.find_npc(text)
                if npc_node is not None:
                    entity = self.knowledge.get_npc(npc_node.npc_id, trace_id=tid)
                    if entity is not None and entity.npc_id not in {
                        item.npc_id for item in npcs
                    }:
                        npcs.append(entity)
                monster_node = self.graph.find_monster(text)
                if monster_node is not None:
                    entity = self.knowledge.get_monster(
                        monster_node.monster_id, trace_id=tid
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
