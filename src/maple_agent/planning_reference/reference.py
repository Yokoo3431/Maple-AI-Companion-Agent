"""Deterministic read-only Planning Reference rules."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from maple_agent.context_reasoning.evidence import effective_lifecycle, graph_node
from maple_agent.context_reasoning.models import (
    ContextEntityReference,
    ContextRelationReference,
    ContextType,
    ContextUnderstanding,
    TemporalState,
)
from maple_agent.game_state.models import (
    EntityLifecycle,
    SemanticEntityReference,
    SemanticGameState,
)
from maple_agent.knowledge_graph.models import Relation, RelationType
from maple_agent.planning_reference.models import (
    PlanningReference,
    PlanningReferenceType,
)


class PlanningReferenceEngine:
    """Translate confirmed semantic context into human-readable references."""

    def generate(
        self,
        semantic_state: SemanticGameState,
        temporal_state: TemporalState | None,
        knowledge_graph: Any,
        context: ContextUnderstanding,
    ) -> list[PlanningReference]:
        """Return information references without proposing a next action."""
        temporal = temporal_state or TemporalState.from_semantic_state(
            semantic_state
        )
        state_references = self._state_references(semantic_state)
        active = [
            reference
            for reference in state_references
            if effective_lifecycle(reference, temporal) is EntityLifecycle.VISIBLE
        ]
        if semantic_state.conflict_evidence_ids or any(
            "conflict" in uncertainty.lower()
            for uncertainty in context.uncertainties
        ):
            return [
                self._make_reference(
                    semantic_state,
                    context,
                    PlanningReferenceType.CONFLICT_NOTICE,
                    "语义候选存在冲突",
                    "当前存在竞争的语义候选，系统保留冲突，不选择其中一个。",
                    context.related_entities,
                    context.related_relations,
                    [
                        "冲突候选未被自动选择",
                        *context.uncertainties,
                    ],
                    "冲突证据被保留为人工审核信息",
                )
            ]

        if not active:
            return [
                self._make_reference(
                    semantic_state,
                    context,
                    PlanningReferenceType.INFORMATION_GAP,
                    "当前信息不足",
                    "当前语义状态不足以确认更多上下文，需要更多观察。",
                    [],
                    [],
                    [
                        "需要更多观察",
                        *context.uncertainties,
                    ],
                    "未知、丢失或过期实体未被解释为当前事实",
                )
            ]

        missing = self._missing_requirements(
            semantic_state,
            temporal,
            knowledge_graph,
            context,
        )
        if missing:
            return missing

        if context.context_type in {
            ContextType.QUEST_RELATED_CONTEXT,
            ContextType.ITEM_QUEST_CONTEXT,
        }:
            return [
                self._make_reference(
                    semantic_state,
                    context,
                    PlanningReferenceType.QUEST_CONTEXT,
                    "当前存在任务相关信息",
                    "当前地图存在与任务关系相关的 NPC。",
                    context.related_entities,
                    context.related_relations,
                    [
                        "玩家是否满足任务条件未确认",
                        *context.uncertainties,
                    ],
                    "仅表示已确认的语义关系，供人工审核",
                )
            ]

        if context.context_type is ContextType.LOCATION_CONTEXT:
            location = semantic_state.location
            entities = [
                entity
                for entity in context.related_entities
                if not entity.historical_only
            ]
            return [
                self._make_reference(
                    semantic_state,
                    context,
                    PlanningReferenceType.KNOWN_LOCATION,
                    "当前地点已确认",
                    f"当前语义状态将地点识别为“{location.display_name if location else '未知'}”。",
                    entities,
                    context.related_relations,
                    [
                        *context.uncertainties,
                        "地点确认不代表任何后续行为",
                    ],
                    "只保留当前地点语义，不推导移动或执行含义",
                )
            ]

        related = [
            entity
            for entity in context.related_entities
            if not entity.historical_only
            and entity.lifecycle is EntityLifecycle.VISIBLE
        ]
        if related:
            return [
                self._make_reference(
                    semantic_state,
                    context,
                    PlanningReferenceType.RELATED_ENTITY,
                    "存在相关实体信息",
                    "当前语义状态包含可追溯的相关实体。",
                    related,
                    context.related_relations,
                    [
                        *context.uncertainties,
                        "实体关系的实际含义仍受知识覆盖限制",
                    ],
                    "仅提供相关实体参考",
                )
            ]

        return [
            self._make_reference(
                semantic_state,
                context,
                PlanningReferenceType.INFORMATION_GAP,
                "当前信息不足",
                "当前语义状态缺少足够的可确认关系，需要更多观察。",
                [],
                [],
                ["需要更多观察", *context.uncertainties],
                "不把未知解释为缺失",
            )
        ]

    def _missing_requirements(
        self,
        state: SemanticGameState,
        temporal: TemporalState,
        graph: Any,
        context: ContextUnderstanding,
    ) -> list[PlanningReference]:
        quests = [
            reference
            for reference in state.quest_context
            if effective_lifecycle(reference, temporal)
            is EntityLifecycle.VISIBLE
        ]
        if not quests:
            return []
        inventory_ids = {
            value
            for reference in state.inventory_references
            if effective_lifecycle(reference, temporal)
            is EntityLifecycle.VISIBLE
            for value in (
                reference.canonical_id,
                self._canonical_id(reference),
            )
        }
        references: list[PlanningReference] = []
        for quest in quests:
            requirements = [
                relation
                for relation in graph.all_relations()
                if relation.relation_type is RelationType.REQUIRES
                and relation.source.strip().lower() == "quest"
                and self._identifier_matches(
                    relation.source_id, quest, "quest"
                )
            ]
            for relation in requirements:
                item_id = str(relation.target_id)
                if item_id in inventory_ids or self._identifier_matches_any(
                    item_id, inventory_ids, "item"
                ):
                    continue
                entities = [
                    entity
                    for entity in context.related_entities
                    if entity.canonical_id == quest.canonical_id
                ]
                item = graph_node(graph, "item", relation.target_id)
                if item is not None:
                    entities.append(
                        self._graph_entity_reference(
                            "item", relation.target_id, item
                        )
                    )
                relation_reference = self._relation_reference(relation)
                references.append(
                    self._make_reference(
                        state,
                        context,
                        PlanningReferenceType.MISSING_REQUIREMENT,
                        "任务条件尚未确认",
                        (
                            f"任务“{quest.display_name}”需要相关物品，但当前"
                            f"未确认拥有“{getattr(item, 'name', item_id)}”。"
                        ),
                        entities,
                        [relation_reference],
                        [
                            "未确认拥有，不等同于已确认缺少",
                            *context.uncertainties,
                        ],
                        "只表达条件信息缺口，不表达任务执行建议",
                    )
                )
        return references

    @staticmethod
    def _state_references(state: SemanticGameState) -> list[SemanticEntityReference]:
        return [
            reference
            for reference in [
                state.location,
                *state.nearby_entities,
                *state.quest_context,
                *state.inventory_references,
                *state.unknown_references,
            ]
            if reference is not None and reference.canonical_id
        ]

    @staticmethod
    def _canonical_id(reference: SemanticEntityReference) -> str:
        prefix = f"{reference.entity_type.strip().lower()}_"
        if reference.canonical_id.startswith(prefix):
            return reference.canonical_id[len(prefix) :]
        return reference.canonical_id

    @classmethod
    def _identifier_matches(
        cls,
        identifier: int | str,
        reference: SemanticEntityReference,
        entity_type: str,
    ) -> bool:
        values = {
            str(reference.canonical_id),
            str(cls._canonical_id(reference)),
        }
        raw_identifier = str(identifier)
        return raw_identifier in values or raw_identifier == (
            f"{entity_type}_{reference.canonical_id}"
        )

    @staticmethod
    def _identifier_matches_any(
        identifier: str,
        known_ids: set[str],
        entity_type: str,
    ) -> bool:
        return identifier in {
            f"{entity_type}_{value}" for value in known_ids
        }

    @staticmethod
    def _relation_reference(
        relation: Relation,
    ) -> ContextRelationReference:
        return ContextRelationReference(
            source_type=relation.source,
            source_id=relation.source_id,
            target_type=relation.target,
            target_id=relation.target_id,
            relation_type=relation.relation_type,
            confidence=relation.confidence,
            provenance=relation.provenance,
        )

    @staticmethod
    def _graph_entity_reference(
        entity_type: str,
        entity_id: int | str,
        node: Any,
    ) -> ContextEntityReference:
        return ContextEntityReference(
            canonical_id=(
                str(entity_id)
                if str(entity_id).startswith(f"{entity_type}_")
                else f"{entity_type}_{entity_id}"
            ),
            entity_type=entity_type,
            display_name=getattr(node, "name", "UNKNOWN"),
            lifecycle=EntityLifecycle.UNKNOWN,
            confidence=getattr(node, "confidence", 0.0),
            relation_confidence=None,
            provenance=getattr(node, "provenance", None),
        )

    @staticmethod
    def _make_reference(
        state: SemanticGameState,
        context: ContextUnderstanding,
        reference_type: PlanningReferenceType,
        title: str,
        description: str,
        entities: Iterable[ContextEntityReference],
        relations: Iterable[ContextRelationReference],
        uncertainties: Iterable[str],
        reasoning_summary: str,
    ) -> PlanningReference:
        entity_list = list(entities)
        relation_list = list(relations)
        confidence_values = [
            state.confidence,
            context.confidence,
            *(entity.confidence for entity in entity_list),
            *(relation.confidence for relation in relation_list),
        ]
        confidence = round(min(confidence_values), 4)
        return PlanningReference(
            reference_id=(
                f"planning-reference-{state.state_id}-"
                f"{reference_type.value.lower()}"
            ),
            reference_type=reference_type,
            title=title,
            description=description,
            supporting_entities=PlanningReferenceEngine._dedupe_entities(
                entity_list
            ),
            supporting_relations=PlanningReferenceEngine._dedupe_relations(
                relation_list
            ),
            source_state_id=state.state_id,
            confidence=confidence,
            uncertainties=list(dict.fromkeys(item for item in uncertainties if item)),
            limitations=[
                "仅供人工审核，不构成下一步行为决定",
            ],
            reasoning_summary=reasoning_summary,
        )

    @staticmethod
    def _dedupe_entities(
        entities: list[ContextEntityReference],
    ) -> list[ContextEntityReference]:
        result: list[ContextEntityReference] = []
        seen: set[str] = set()
        for entity in entities:
            if entity.canonical_id not in seen:
                seen.add(entity.canonical_id)
                result.append(entity)
        return result

    @staticmethod
    def _dedupe_relations(
        relations: list[ContextRelationReference],
    ) -> list[ContextRelationReference]:
        result: list[ContextRelationReference] = []
        seen: set[tuple[str, str, str, str, str]] = set()
        for relation in relations:
            key = (
                relation.source_type,
                str(relation.source_id),
                relation.target_type,
                str(relation.target_id),
                relation.relation_type.value,
            )
            if key not in seen:
                seen.add(key)
                result.append(relation)
        return result
