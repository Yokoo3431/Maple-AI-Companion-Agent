"""Phase 13-J canonical graph, evidence resolution and semantic state tests."""

from __future__ import annotations

import json

from maple_agent.game_state import (
    CurrentObservation,
    PlayerStateReference,
    SemanticStateResolver,
    save_semantic_state_trace,
)
from maple_agent.hybrid_vision import (
    EvidenceResolver,
    PerceptionEvidence,
    ResolutionMatchType,
)
from maple_agent.knowledge.importer import run_import
from maple_agent.knowledge.importer.models import ImportSource
from maple_agent.knowledge_quality import (
    KnowledgeQualityBenchmark,
    KnowledgeReadinessPolicy,
    build_knowledge_readiness,
)
from maple_agent.maple_knowledge import (
    KnowledgeImporter,
    MapleKnowledgeBase,
    MapleKnowledgeGraph,
    load_phase13j_fixture,
)
from maple_agent.maple_knowledge.models import (
    MapleKnowledgeEntity,
    MapleKnowledgeType,
)


def _graph() -> MapleKnowledgeGraph:
    entities, relations = load_phase13j_fixture()
    base = MapleKnowledgeBase()
    for entity in entities:
        base.add_entity(entity)
    for relation in relations:
        base.add_relation(relation)
    return MapleKnowledgeGraph(base)


def test_fixture_covers_phase13j_entity_types_and_provenance():
    graph = _graph()
    types = {entity.knowledge_type for entity in graph.all_entities()}
    assert types == {
        MapleKnowledgeType.MAP,
        MapleKnowledgeType.NPC,
        MapleKnowledgeType.MONSTER,
        MapleKnowledgeType.ITEM,
        MapleKnowledgeType.EQUIPMENT,
        MapleKnowledgeType.QUEST,
        MapleKnowledgeType.STORY_LORE,
    }
    assert len(graph.all_entities()) >= 20
    assert all(
        entity.knowledge_id
        and entity.name
        and entity.provenance.source_id
        and entity.provenance.data_version
        and entity.version
        for entity in graph.all_entities()
    )


def test_alias_resolution_preserves_observation():
    evidence = PerceptionEvidence(
        evidence_id="e-npc",
        evidence_type="npc",
        value="弓箭手教官",
        confidence=0.8,
        source="fixture",
        raw_value="弓箭手教官",
    )
    result = EvidenceResolver().resolve(evidence, _graph(), knowledge_type="NPC")
    assert result.resolved is True
    assert result.selected is not None
    assert result.selected.canonical_id == "npc_heena"
    assert result.selected.match_type is ResolutionMatchType.ALIAS
    assert result.selected.resolution_confidence == 0.76
    assert evidence.value == "弓箭手教官"
    assert result.observed_value == "弓箭手教官"


def test_unknown_entity_remains_unresolved():
    result = EvidenceResolver().resolve(
        PerceptionEvidence(
            evidence_id="e-unknown",
            evidence_type="npc",
            value="未知 NPC",
            confidence=0.95,
        ),
        _graph(),
    )
    assert result.resolved is False
    assert result.selected is None
    assert result.candidates == []


def test_semantic_state_keeps_evidence_and_separates_categories():
    observation = CurrentObservation(
        observation_id="obs-13j",
        evidence=[
            PerceptionEvidence(
                evidence_id="e-map",
                evidence_type="location",
                value="Henesys",
                confidence=0.9,
            ),
            PerceptionEvidence(
                evidence_id="e-npc",
                evidence_type="npc",
                value="赫丽娜",
                confidence=0.85,
            ),
            PerceptionEvidence(
                evidence_id="e-quest",
                evidence_type="quest",
                value="Sap Collection",
                confidence=0.8,
            ),
            PerceptionEvidence(
                evidence_id="e-item",
                evidence_type="inventory",
                value="红瓶",
                confidence=0.8,
            ),
            PerceptionEvidence(
                evidence_id="e-unknown",
                evidence_type="npc",
                value="未登记对象",
                confidence=0.8,
            ),
        ],
        player_status=PlayerStateReference(hp=0.9, mp=0.75, level_reference=8),
    )
    state = SemanticStateResolver(_graph()).resolve(observation)
    assert state.location is not None
    assert state.location.canonical_id == "map_100000000"
    assert [item.canonical_id for item in state.nearby_entities] == ["npc_heena"]
    assert [item.canonical_id for item in state.quest_context] == ["quest_collect_sap"]
    assert [item.canonical_id for item in state.inventory_references] == [
        "item_potion_red"
    ]
    assert state.player_status is not None
    assert state.player_status.hp == 0.9
    assert state.unresolved_evidence_ids == ["e-unknown"]
    assert [item.evidence_id for item in state.evidence] == [
        item.evidence_id for item in observation.evidence
    ]
    assert not hasattr(state, "action")


def test_duplicate_canonical_id_is_reported_without_overwrite():
    importer = KnowledgeImporter()
    entities = importer.import_entities(
        {
            "entities": [
                {"knowledge_id": "npc-1", "knowledge_type": "NPC", "name": "甲"},
                {"knowledge_id": "npc-1", "knowledge_type": "NPC", "name": "乙"},
            ]
        }
    )
    assert len(entities) == 1
    assert importer.last_conflicts == ["duplicate canonical id: npc-1"]

    base = MapleKnowledgeBase()
    base.add_entity(entities[0])
    base.add_entity(
        MapleKnowledgeEntity(
            knowledge_id="npc-1",
            knowledge_type=MapleKnowledgeType.NPC,
            name="乙",
        )
    )
    assert base.get_entity("npc-1").name == "甲"
    assert base.conflicts() == ["duplicate canonical id: npc-1"]


def test_generic_import_pipeline_supports_new_entity_types(tmp_path):
    packet = {
        "equipment": [{"equipment_id": "eq-1", "name": "测试短剑"}],
        "quests": [{"quest_id": "q-1", "name": "测试任务"}],
        "story_lore": [{"lore_id": "l-1", "name": "测试传说"}],
        "relations": [
            {
                "source": "quest",
                "source_id": "q-1",
                "target": "equipment",
                "target_id": "eq-1",
                "relation_type": "USES",
            }
        ],
    }
    bundle = run_import(
        packet,
        source=ImportSource(source_id="phase13j", version="fixture-v1"),
        sessions_dir=tmp_path,
    )
    assert bundle.validation.valid is True
    assert len(bundle.dataset.equipment) == 1
    assert len(bundle.dataset.quests) == 1
    assert len(bundle.dataset.story_lore) == 1
    assert bundle.dataset.equipment[0].provenance.source_id == "phase13j"


def test_semantic_quality_metrics_and_automatic_readiness():
    graph = _graph()
    evidence = [
        PerceptionEvidence(
            evidence_id="e-known",
            evidence_type="npc",
            value="Helena",
            confidence=0.8,
        ),
        PerceptionEvidence(
            evidence_id="e-unknown",
            evidence_type="npc",
            value="未知",
            confidence=0.8,
        ),
    ]
    resolutions = [EvidenceResolver().resolve(item, graph) for item in evidence]
    benchmark = KnowledgeQualityBenchmark().evaluate_semantic_graph(
        graph,
        resolutions,
        expected_canonical_ids={item.knowledge_id for item in graph.all_entities()},
    )
    assert benchmark.canonical_id_coverage == 1.0
    assert benchmark.provenance_coverage == 1.0
    assert benchmark.unresolved_reference_rate == 0.5
    assert benchmark.conflict_rate == 0.0
    assert benchmark.equipment_count == 4
    assert benchmark.story_lore_count == 3
    readiness = build_knowledge_readiness(
        benchmark,
        policy=KnowledgeReadinessPolicy(minimum_total_entities=20),
        game_profile="maple-v113",
        server_version="fixture",
        dataset_version="fixture-v1",
        source_provenance="phase13j-fixture",
        denominators=None,
    )
    assert readiness.status.value == "FOUNDATION_ONLY"


def test_semantic_state_replay_is_sanitized(tmp_path):
    state = SemanticStateResolver(_graph()).resolve(
        CurrentObservation(
            observation_id="obs-replay",
            evidence=[
                PerceptionEvidence(
                    evidence_id="e1",
                    evidence_type="location",
                    value="射手村",
                    confidence=0.9,
                )
            ],
        )
    )
    save_semantic_state_trace(tmp_path, "trace-13j", state)
    payload = json.loads(
        (tmp_path / "trace-13j" / "semantic_game_state.json").read_text(
            encoding="utf-8"
        )
    )
    assert payload["schema_version"] == "1.0"
    assert payload["state"]["observation_id"] == "obs-replay"
    assert "screenshot" not in json.dumps(payload, ensure_ascii=False).lower()
