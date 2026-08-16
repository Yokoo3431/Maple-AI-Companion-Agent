"""Phase 13-O deterministic context reasoning contract tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime

from maple_agent.context_reasoning import (
    ContextReasoner,
    ContextReasoningBenchmark,
    ContextType,
    TemporalState,
)
from maple_agent.game_state.models import (
    EntityLifecycle,
    SemanticEntityReference,
    SemanticGameState,
)
from maple_agent.knowledge.importer.builder import build_dataset
from maple_agent.knowledge_graph import (
    ItemNode,
    KnowledgeEntityProvenance,
    KnowledgeGraph,
    MapNode,
    NPCNode,
    QuestNode,
    Relation,
    RelationType,
)
from maple_agent.knowledge_quality import KnowledgeDatasetPackage

NOW = datetime(2026, 8, 16, 12, 0, tzinfo=UTC)


def _provenance() -> KnowledgeEntityProvenance:
    return KnowledgeEntityProvenance(
        source_id="phase13o-test",
        source_type="TEST_FIXTURE",
        game_profile="maple-cms-classic-community",
        server_profile="cn-nostalgic-community",
        data_version="phase13o-test-v1",
    )


def _graph(*, two_quests: bool = False, low_contains: bool = False) -> KnowledgeGraph:
    provenance = _provenance()
    quests = [
        QuestNode(
            quest_id="q1",
            name="任务一",
            confidence=0.9,
            provenance=provenance,
        )
    ]
    relations = [
        Relation(
            source="map",
            source_id="m1",
            target="npc",
            target_id="n1",
            relation_type=RelationType.CONTAINS,
            confidence=0.5 if low_contains else 0.9,
            provenance=provenance,
        ),
        Relation(
            source="npc",
            source_id="n1",
            target="quest",
            target_id="q1",
            relation_type=RelationType.GIVES,
            confidence=0.82,
            provenance=provenance,
        ),
        Relation(
            source="quest",
            source_id="q1",
            target="item",
            target_id="i1",
            relation_type=RelationType.REQUIRES,
            confidence=0.88,
            provenance=provenance,
        ),
    ]
    if two_quests:
        quests.append(
            QuestNode(
                quest_id="q2",
                name="任务二",
                confidence=0.9,
                provenance=provenance,
            )
        )
        relations.append(
            Relation(
                source="npc",
                source_id="n1",
                target="quest",
                target_id="q2",
                relation_type=RelationType.GIVES,
                confidence=0.81,
                provenance=provenance,
            )
        )
    return KnowledgeGraph(
        maps=[MapNode(map_id="m1", name="测试地图", confidence=0.95, provenance=provenance)],
        npcs=[NPCNode(npc_id="n1", name="测试 NPC", confidence=0.9, provenance=provenance)],
        quests=quests,
        items=[ItemNode(item_id="i1", name="测试物品", confidence=0.9, provenance=provenance)],
        relations=relations,
    )


def _reference(
    canonical_id: str,
    entity_type: str,
    name: str,
    *,
    lifecycle: EntityLifecycle = EntityLifecycle.VISIBLE,
    confidence: float = 0.9,
) -> SemanticEntityReference:
    return SemanticEntityReference(
        canonical_id=canonical_id,
        entity_type=entity_type,
        display_name=name,
        lifecycle=lifecycle,
        confidence=confidence,
    )


def _state(
    *,
    include_location: bool = True,
    location_lifecycle: EntityLifecycle = EntityLifecycle.VISIBLE,
    include_npc: bool = True,
    include_quest: bool = False,
    include_item: bool = False,
    unknown: bool = False,
) -> SemanticGameState:
    return SemanticGameState(
        state_id="state-13o",
        observation_id="observation-13o",
        timestamp=NOW,
        location=(
            _reference(
                "map_m1",
                "map",
                "测试地图",
                lifecycle=location_lifecycle,
            )
            if include_location
            else None
        ),
        nearby_entities=(
            [_reference("npc_n1", "npc", "测试 NPC")]
            if include_npc
            else []
        ),
        quest_context=(
            [_reference("quest_q1", "quest", "任务一")]
            if include_quest
            else []
        ),
        inventory_references=(
            [_reference("item_i1", "item", "测试物品")]
            if include_item
            else []
        ),
        unknown_references=(
            [_reference("", "npc", "未登记对象", lifecycle=EntityLifecycle.UNKNOWN)]
            if unknown
            else []
        ),
        confidence=0.9,
        history_size=3,
    )


def test_location_npc_quest_relation_produces_quest_context():
    context = ContextReasoner(_graph()).reason(_state())

    assert context.context_type is ContextType.QUEST_RELATED_CONTEXT
    assert {item.canonical_id for item in context.related_entities} >= {
        "map_m1",
        "npc_n1",
        "quest_q1",
    }
    assert {item.relation_type for item in context.related_relations} == {
        RelationType.CONTAINS,
        RelationType.GIVES,
    }
    assert context.confidence == 0.82
    assert all(item.provenance.source_id == "phase13o-test" for item in context.related_relations)


def test_visible_quest_and_inventory_item_produce_item_quest_context():
    context = ContextReasoner(_graph()).reason(
        _state(include_npc=False, include_quest=True, include_item=True)
    )

    assert context.context_type is ContextType.ITEM_QUEST_CONTEXT
    assert len(context.related_relations) == 1
    assert context.related_relations[0].relation_type is RelationType.REQUIRES


def test_real_community_snapshot_feeds_context_reasoning():
    package = KnowledgeDatasetPackage.load("knowledge_dataset")
    dataset, _ = build_dataset(
        package.packet,
        source=package.manifest.source_id,
        version=package.manifest.dataset_version,
    )
    contains = next(
        relation
        for relation in dataset.relations
        if relation.relation_type is RelationType.CONTAINS
        and any(
            candidate.relation_type is RelationType.GIVES
            and str(candidate.source_id) == str(relation.target_id)
            for candidate in dataset.relations
        )
    )
    graph = KnowledgeGraph(
        maps=dataset.maps,
        npcs=dataset.npcs,
        monsters=dataset.monsters,
        items=dataset.items,
        equipment=dataset.equipment,
        quests=dataset.quests,
        story_lore=dataset.story_lore,
        relations=dataset.relations,
    )
    state = SemanticGameState(
        state_id="state-real-13o",
        observation_id="observation-real-13o",
        timestamp=NOW,
        location=_reference(f"map_{contains.source_id}", "map", "快照地图"),
        nearby_entities=[
            _reference(f"npc_{contains.target_id}", "npc", "快照 NPC")
        ],
        confidence=0.9,
    )

    context = ContextReasoner(graph).reason(state)
    assert context.context_type is ContextType.QUEST_RELATED_CONTEXT
    assert context.related_relations
    assert all(
        relation.provenance.source_id == package.manifest.source_id
        for relation in context.related_relations
    )


def test_unknown_entity_remains_unknown_context():
    context = ContextReasoner(_graph()).reason(
        _state(include_location=False, include_npc=False, unknown=True)
    )

    assert context.context_type is ContextType.UNKNOWN_CONTEXT
    assert context.related_entities[0].lifecycle is EntityLifecycle.UNKNOWN
    assert context.uncertainties


def test_conflicting_relation_preserves_uncertainty_and_candidates():
    context = ContextReasoner(_graph(two_quests=True)).reason(_state())

    assert context.context_type is ContextType.QUEST_RELATED_CONTEXT
    given_quests = {
        item.target_id
        for item in context.related_relations
        if item.relation_type is RelationType.GIVES
    }
    assert given_quests == {
        "q1",
        "q2",
    }
    assert any("multiple quest relation candidates" in item for item in context.uncertainties)


def test_expired_entity_does_not_create_active_context():
    state = _state(location_lifecycle=EntityLifecycle.EXPIRED, include_npc=False)
    context = ContextReasoner(_graph()).reason(state, TemporalState.from_semantic_state(state))

    assert context.context_type is ContextType.UNKNOWN_CONTEXT
    assert not context.related_entities
    assert any("expired" in item for item in context.uncertainties)


def test_lost_entity_is_historical_only():
    state = _state(location_lifecycle=EntityLifecycle.LOST, include_npc=False)
    context = ContextReasoner(_graph()).reason(state)

    assert context.context_type is ContextType.UNKNOWN_CONTEXT
    assert context.related_entities[0].historical_only is True
    assert context.related_entities[0].lifecycle is EntityLifecycle.LOST
    assert any("historical" in item for item in context.uncertainties)


def test_low_confidence_relation_is_not_promoted():
    context = ContextReasoner(_graph(low_contains=True)).reason(_state())

    assert context.context_type is ContextType.LOCATION_CONTEXT
    assert context.related_relations == []
    assert any("below confidence threshold" in item for item in context.uncertainties)


def test_temporal_projection_and_benchmark_have_explicit_metrics():
    context = ContextReasoner(_graph()).reason(_state())
    temporal = TemporalState.from_semantic_state(_state())
    benchmark = ContextReasoningBenchmark.evaluate([context])

    assert temporal.history_size == 3
    assert temporal.lifecycle_by_entity["map_m1"] is EntityLifecycle.VISIBLE
    assert benchmark.total_contexts == 1
    assert benchmark.promotion_rate == 1.0
    assert benchmark.relation_provenance_coverage == 1.0


def test_context_output_has_no_action_or_execution_leakage():
    payload = json.dumps(
        ContextReasoner(_graph()).reason(_state()).model_dump(mode="json"),
        ensure_ascii=False,
    ).lower()

    for forbidden in ("command", "action", "input", "executor", "key", "mouse"):
        assert forbidden not in payload
