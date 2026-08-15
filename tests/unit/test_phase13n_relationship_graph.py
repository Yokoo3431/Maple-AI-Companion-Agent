"""Phase 13-N relationship graph and planning-reference contract tests."""

from __future__ import annotations

from maple_agent.game_state.models import SemanticEntityReference, SemanticGameState
from maple_agent.hybrid_vision import EvidenceResolver, PerceptionEvidence
from maple_agent.knowledge.importer.builder import build_dataset
from maple_agent.knowledge_graph import (
    ItemNode,
    KnowledgeEntityProvenance,
    KnowledgeGraph,
    KnowledgeGraphValidator,
    MapNode,
    NPCNode,
    PlanningContext,
    QuestNode,
    Relation,
    RelationType,
    validate_relation_records,
)
from maple_agent.knowledge_quality import (
    KnowledgeDatasetPackage,
    KnowledgeSourceReference,
    KnowledgeSourceType,
)
from maple_agent.knowledge_quality.source import sanitize_source_metadata
from maple_agent.maple_knowledge import (
    MapleKnowledgeBase,
    MapleKnowledgeGraph,
    load_phase13j_fixture,
)

PACKAGE_DIR = "knowledge_dataset"


def _provenance() -> KnowledgeEntityProvenance:
    return KnowledgeEntityProvenance(
        source_id="phase13n-test",
        source_type="TEST_FIXTURE",
        game_profile="maple-cms-classic-community",
        server_profile="cn-nostalgic-community",
        data_version="phase13n-test-v1",
    )


def _graph() -> KnowledgeGraph:
    provenance = _provenance()
    return KnowledgeGraph(
        maps=[MapNode(map_id="m1", name="测试地图", provenance=provenance)],
        npcs=[NPCNode(npc_id="n1", name="测试 NPC", provenance=provenance)],
        quests=[QuestNode(quest_id="q1", name="测试任务", provenance=provenance)],
        items=[ItemNode(item_id="i1", name="测试物品", provenance=provenance)],
        relations=[
            Relation(
                source="map",
                source_id="m1",
                target="npc",
                target_id="n1",
                relation_type=RelationType.CONTAINS,
                provenance=provenance,
                confidence=0.9,
            ),
            Relation(
                source="npc",
                source_id="n1",
                target="quest",
                target_id="q1",
                relation_type=RelationType.GIVES,
                provenance=provenance,
                confidence=0.8,
            ),
            Relation(
                source="quest",
                source_id="q1",
                target="item",
                target_id="i1",
                relation_type=RelationType.REQUIRES,
                provenance=provenance,
                confidence=0.85,
            ),
            Relation(
                source="quest",
                source_id="q1",
                target="item",
                target_id="i1",
                relation_type=RelationType.REWARDS,
                provenance=provenance,
                confidence=0.7,
            ),
        ],
    )


def test_relation_model_and_read_only_queries_preserve_provenance():
    graph = _graph()

    assert [item.entity_id for item in graph.related_npcs("map", "m1")] == ["n1"]
    assert [item.entity_id for item in graph.related_quests("npc", "n1")] == ["q1"]
    items = graph.related_items("quest", "q1")
    assert {item.relation_type for item in items} == {
        RelationType.REQUIRES,
        RelationType.REWARDS,
    }
    assert all(item.provenance.source_id == "phase13n-test" for item in items)


def test_graph_validator_accepts_valid_graph_and_rejects_bad_edges():
    result = KnowledgeGraphValidator().validate(_graph())
    assert result.valid is True
    assert result.edge_count == 4
    assert result.missing_provenance_count == 0

    bad_records = [
        {
            "source": "map",
            "source_id": "m1",
            "target": "npc",
            "target_id": "missing",
            "relation_type": "CONTAINS",
            "confidence": 0.9,
            "provenance": _provenance().model_dump(mode="json"),
        },
        {
            "source": "map",
            "source_id": "m1",
            "target": "npc",
            "target_id": "missing",
            "relation_type": "CONTAINS",
            "confidence": 0.9,
            "provenance": _provenance().model_dump(mode="json"),
        },
        {
            "source": "map",
            "source_id": "m1",
            "target": "item",
            "target_id": "i1",
            "relation_type": "NOT_A_RELATION",
        },
        {
            "source": "map",
            "source_id": "m1",
            "target": "item",
            "target_id": "i1",
            "relation_type": "CONTAINS",
            "confidence": 0.9,
            "provenance": _provenance().model_dump(mode="json"),
        },
    ]
    result = validate_relation_records(
        bad_records,
        {"map": {"m1"}, "npc": {"n1"}, "item": {"i1"}},
    )
    assert result.valid is False
    assert result.duplicate_edge_count == 1
    assert result.dangling_reference_count == 2
    assert result.invalid_relation_type_count == 1
    assert result.invalid_endpoint_count == 1
    assert result.missing_provenance_count == 1


def test_real_package_relations_reuse_import_pipeline_and_graph_validator():
    package = KnowledgeDatasetPackage.load(PACKAGE_DIR)
    validation = package.validate()
    assert validation.valid is True
    assert validation.relation_count == 132
    assert validation.duplicate_edge_count == 0
    assert validation.dangling_relation_count == 0
    assert validation.missing_relation_provenance_count == 0

    dataset, import_result = build_dataset(
        package.packet,
        source=package.manifest.source_id,
        version=package.manifest.dataset_version,
    )
    assert import_result.imported_relations == 132
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
    assert KnowledgeGraphValidator().validate(graph).valid is True


def test_planning_context_contains_references_but_no_commands():
    graph = _graph()
    state = SemanticGameState(
        state_id="state-13n",
        observation_id="obs-13n",
        location=SemanticEntityReference(
            canonical_id="map_m1",
            entity_type="map",
            display_name="测试地图",
        ),
    )

    context = PlanningContext.from_state(graph, state)
    assert context.current_semantic_state is state
    assert {item.entity_type for item in context.relevant_knowledge} == {"npc"}
    assert context.possible_references["npcs"][0].entity_id == "n1"
    assert not {"action", "command", "input", "executor"}.intersection(
        PlanningContext.model_fields
    )


def test_existing_phase13j_resolver_remains_the_only_resolver():
    entities, relations = load_phase13j_fixture()
    base = MapleKnowledgeBase()
    for entity in entities:
        base.add_entity(entity)
    for relation in relations:
        base.add_relation(relation)
    resolution = EvidenceResolver().resolve(
        PerceptionEvidence(
            evidence_id="e-13n",
            evidence_type="npc",
            value="弓箭手教官",
            confidence=0.8,
        ),
        MapleKnowledgeGraph(base),
        knowledge_type="NPC",
    )
    assert resolution.resolved is True
    assert resolution.selected is not None
    assert resolution.selected.canonical_id == "npc_heena"


def test_relation_provenance_sanitizer_does_not_leak_private_paths():
    source = KnowledgeSourceReference(
        source_id="phase13n-test",
        source_type=KnowledgeSourceType.LOCAL_STATIC_FILE,
        source_reference=r"C:\private\session.json",
    )
    sanitized = sanitize_source_metadata(source)
    assert sanitized["source_reference"] == "<REDACTED_PATH>"
    assert "private" not in str(sanitized).lower()
