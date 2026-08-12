"""MaplePerceptionBinder:感知实体 + 领域知识 -> MaplePerceptionReference(只读)。"""

from __future__ import annotations

import json
from pathlib import Path

from maple_agent.architecture import TRACE_SCHEMA_VERSION
from maple_agent.maple_knowledge.knowledge_base import MapleKnowledgeGraph
from maple_agent.maple_knowledge.models import MapleKnowledgeType
from maple_agent.perception.analyzer import ObservationAnalyzer
from maple_agent.perception.models import (
    MaplePerceptionReference,
    PerceivedEntity,
    PerceivedEntityType,
    VisualObservation,
)


class MaplePerceptionBinder:
    """把视觉观察与 Maple 领域知识绑定为感知参考。"""

    def __init__(
        self,
        *,
        knowledge: MapleKnowledgeGraph | None = None,
        analyzer: ObservationAnalyzer | None = None,
    ) -> None:
        self.knowledge = knowledge
        self.analyzer = analyzer or ObservationAnalyzer()
        self.last_reference: MaplePerceptionReference | None = None

    def bind(
        self,
        observation: VisualObservation,
    ) -> MaplePerceptionReference:
        entities = self.analyzer.analyze(observation, self.knowledge)
        visible_map = next(
            (
                entity.name
                for entity in entities
                if entity.entity_type is PerceivedEntityType.MAP_LABEL
            ),
            "",
        )
        visible_entities = [
            entity
            for entity in entities
            if entity.entity_type
            in (
                PerceivedEntityType.NPC,
                PerceivedEntityType.MONSTER,
                PerceivedEntityType.ITEM,
                PerceivedEntityType.UNKNOWN,
            )
        ]
        related_knowledge = self._related_knowledge(
            visible_entities,
            visible_map,
        )
        ui_state_reference = {
            entity.name: entity.attributes
            for entity in entities
            if entity.entity_type is PerceivedEntityType.UI_ELEMENT
        }
        confidence = self._confidence(observation, related_knowledge)
        reasoning = self._reasoning(
            visible_map,
            visible_entities,
            related_knowledge,
        )
        reference = MaplePerceptionReference(
            observation_id=observation.observation_id,
            visible_entities=visible_entities,
            visible_map=visible_map,
            ui_state_reference=ui_state_reference,
            related_knowledge=related_knowledge,
            confidence=confidence,
            reasoning=reasoning,
        )
        self.last_reference = reference
        return reference

    def _related_knowledge(
        self,
        visible_entities: list[PerceivedEntity],
        visible_map: str,
    ) -> dict:
        related: dict[str, list[str]] = {
            "npc": [],
            "map": [],
            "monster": [],
            "item": [],
            "quest": [],
        }
        if self.knowledge is None:
            return related
        for entity in visible_entities:
            knowledge_entity = self.knowledge.find_by_name(entity.name)
            if knowledge_entity is None:
                continue
            if knowledge_entity.knowledge_type is MapleKnowledgeType.NPC:
                related["npc"].append(knowledge_entity.name)
            elif (
                knowledge_entity.knowledge_type
                is MapleKnowledgeType.MONSTER
            ):
                related["monster"].append(knowledge_entity.name)
            elif knowledge_entity.knowledge_type is MapleKnowledgeType.ITEM:
                related["item"].append(knowledge_entity.name)
        if visible_map and self.knowledge.find_by_name(visible_map) is not None:
            related["map"].append(visible_map)
            self._collect_quests(visible_map, related)
        for npc in related["npc"]:
            self._collect_quests(npc, related)
        return {key: sorted(set(value)) for key, value in related.items()}

    def _collect_quests(
        self,
        anchor_name: str,
        related: dict[str, list[str]],
    ) -> None:
        anchor = self.knowledge.find_by_name(anchor_name)
        if anchor is None:
            return
        anchors = {anchor_name, anchor.name}
        for entity in self.knowledge.all_entities():
            if entity.knowledge_type is not MapleKnowledgeType.QUEST:
                continue
            for relation, target in self.knowledge.find_related(
                entity.knowledge_id
            ):
                if target.name in anchors:
                    related["quest"].append(entity.name)
                    break

    @staticmethod
    def _confidence(
        observation: VisualObservation,
        related: dict,
    ) -> float:
        base = observation.confidence
        if any(related.values()):
            base = min(1.0, base + 0.05)
        return round(base, 4)

    @staticmethod
    def _reasoning(
        visible_map: str,
        visible_entities: list[PerceivedEntity],
        related: dict,
    ) -> list[str]:
        parts: list[str] = []
        if visible_map:
            parts.append(f"识别地图: {visible_map}")
        if visible_entities:
            parts.append(
                "可见实体: "
                + ", ".join(entity.name for entity in visible_entities)
            )
        if related["quest"]:
            parts.append("关联任务: " + ", ".join(related["quest"]))
        return parts


def save_perception_trace(
    sessions_dir: str | Path,
    trace_id: str,
    *,
    observation: VisualObservation,
    entities: list[PerceivedEntity],
    knowledge_binding: MaplePerceptionReference,
    validation: str,
) -> None:
    """写入 perception_trace.json(统一 Replay)。"""
    directory = Path(sessions_dir) / trace_id
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "observation": observation.model_dump(mode="json"),
        "entities": [
            entity.model_dump(mode="json") for entity in entities
        ],
        "knowledge_binding": knowledge_binding.model_dump(mode="json"),
        "validation": validation,
    }
    (directory / "perception_trace.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
