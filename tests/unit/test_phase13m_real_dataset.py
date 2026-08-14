"""Phase 13-M real snapshot, validation and compatibility tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from maple_agent.game_state import (
    CurrentObservation,
    ObservationHistory,
    StateReducer,
)
from maple_agent.hybrid_vision import EvidenceResolver, PerceptionEvidence
from maple_agent.knowledge_quality import (
    CanonicalMapper,
    KnowledgeDatasetPackage,
    KnowledgeDatasetPackageAdapter,
    KnowledgeImportOrchestrator,
    KnowledgeSourceType,
    content_hash,
    sanitize_source_metadata,
)
from maple_agent.maple_knowledge import (
    MapleKnowledgeEntity,
    MapleKnowledgeGraph,
    MapleKnowledgeType,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_DIR = REPO_ROOT / "knowledge_dataset"
ENTITY_KEYS = (
    "maps",
    "npcs",
    "monsters",
    "items",
    "equipment",
    "quests",
    "story_lore",
    "relations",
)


def _minimal_package(tmp_path: Path, packet: dict) -> KnowledgeDatasetPackage:
    package_dir = tmp_path / "package"
    entities_dir = package_dir / "entities"
    entities_dir.mkdir(parents=True)
    for key in ENTITY_KEYS:
        (entities_dir / f"{key}.json").write_text(
            json.dumps(packet.get(key, []), ensure_ascii=False),
            encoding="utf-8",
        )
    canonical = []
    for entity_type, id_field in (
        ("maps", "map_id"),
        ("npcs", "npc_id"),
        ("items", "item_id"),
        ("quests", "quest_id"),
    ):
        for item in packet.get(entity_type, []):
            canonical.append(
                {
                    "canonical_id": f"{entity_type[:-1]}_{item[id_field]}",
                    "entity_type": entity_type[:-1].upper(),
                    "display_name": item["name"],
                    "aliases": item.get("aliases", []),
                }
            )
    (package_dir / "canonical_entities.json").write_text(
        json.dumps(canonical, ensure_ascii=False),
        encoding="utf-8",
    )
    counts = {
        key: len(packet.get(key, []))
        for key in ENTITY_KEYS
        if key != "relations"
    }
    manifest = {
        "schema_version": "1.0",
        "dataset_version": "test-v1",
        "source_id": "test-source",
        "source_name": "test source",
        "source_type": "MANUAL_CURATED",
        "source_reference": "https://example.invalid/source",
        "game_profile": "maple-v113",
        "server_profile": "test-server",
        "snapshot_version": "test-snapshot",
        "content_hash": content_hash(packet),
        "entity_counts": counts,
        "expected_counts": {key: value for key, value in counts.items() if value},
        "provenance_fields": [
            "source_id",
            "source_type",
            "game_profile",
            "server_profile",
            "data_version",
        ],
        "sanitized": True,
    }
    (package_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False),
        encoding="utf-8",
    )
    return KnowledgeDatasetPackage.load(package_dir)


def _entity(entity_id: str, name: str, **extra) -> dict:
    return {
        "map_id": entity_id,
        "name": name,
        "aliases": [],
        "provenance": {
            "source_id": "test-source",
            "source_type": "MANUAL_CURATED",
            "game_profile": "maple-v113",
            "server_profile": "test-server",
            "data_version": "test-v1",
        },
        **extra,
    }


def test_real_chinese_snapshot_schema_and_quality():
    package = KnowledgeDatasetPackage.load(PACKAGE_DIR)
    validation = package.validate()

    assert validation.valid is True
    assert validation.actual_counts == {
        "maps": 50,
        "npcs": 100,
        "monsters": 0,
        "items": 200,
        "equipment": 0,
        "quests": 50,
        "story_lore": 0,
    }
    assert validation.coverage["items"] == 1.0
    assert validation.provenance_coverage == 1.0
    assert validation.duplicate_id_count == 0
    assert validation.alias_conflict_count == 0
    assert validation.missing_reference_count == 129
    assert package.manifest.source_type is KnowledgeSourceType.COMMUNITY_DATABASE
    assert package.manifest.source_reference == "https://mxdc.dvg.cn/"


def test_real_snapshot_reuses_adapter_importer_and_canonical_mapping():
    package = KnowledgeDatasetPackage.load(PACKAGE_DIR)
    result = KnowledgeImportOrchestrator(
        canonical_mapper=CanonicalMapper(package.canonical_mapper_entities())
    ).acquire(
        package.source_reference(),
        KnowledgeDatasetPackageAdapter(),
        source_id_mapping=package.canonical_source_id_mapping(),
        denominators=[package.denominator()],
    )

    assert result.dataset is not None
    assert result.manifest.entity_counts == {
        "map": 50,
        "npc": 100,
        "monster": 0,
        "item": 200,
        "equipment": 0,
        "quest": 50,
        "story_lore": 0,
    }
    assert result.benchmark is not None
    assert result.benchmark.entity_coverage == 1.0
    assert result.benchmark.canonical_id_coverage == 1.0
    assert result.benchmark.provenance_coverage == 1.0
    assert result.benchmark.unresolved_reference_rate == 0.0
    assert result.readiness is not None
    assert result.readiness.status.value == "FOUNDATION_ONLY"


def test_real_snapshot_works_with_phase13j_resolver_and_phase13k_memory():
    package = KnowledgeDatasetPackage.load(PACKAGE_DIR)
    result = KnowledgeImportOrchestrator().acquire(
        package.source_reference(),
        KnowledgeDatasetPackageAdapter(),
    )
    assert result.dataset is not None
    graph = MapleKnowledgeGraph()
    entity_sets = (
        ("map", "map_id", MapleKnowledgeType.MAP, result.dataset.maps),
        ("npc", "npc_id", MapleKnowledgeType.NPC, result.dataset.npcs),
        ("item", "item_id", MapleKnowledgeType.ITEM, result.dataset.items),
        ("quest", "quest_id", MapleKnowledgeType.QUEST, result.dataset.quests),
    )
    for prefix, id_field, entity_type, entities in entity_sets:
        for entity in entities:
            graph.add_entity(
                MapleKnowledgeEntity(
                    knowledge_id=f"{prefix}_{getattr(entity, id_field)}",
                    knowledge_type=entity_type,
                    name=entity.name,
                    aliases=list(entity.aliases),
                    description=getattr(entity, "description", ""),
                    source=entity.provenance.source_id,
                    confidence=entity.confidence,
                    version=entity.version,
                    provenance=entity.provenance.model_dump(),
                )
            )

    npc = result.dataset.npcs[0]
    evidence = PerceptionEvidence(
        evidence_id="phase13m-npc",
        evidence_type="npc",
        value=npc.name,
        confidence=0.8,
    )
    resolution = EvidenceResolver().resolve(evidence, graph)
    assert resolution.resolved is True
    assert resolution.selected is not None
    assert resolution.selected.canonical_id == f"npc_{npc.npc_id}"

    timestamp = datetime(2026, 8, 14, tzinfo=UTC)
    history = ObservationHistory()
    history.add_observation(
        CurrentObservation(
            observation_id="phase13m-observation",
            timestamp=timestamp,
            evidence=[evidence],
            source="sanitized-fixture",
        ),
        [resolution],
    )
    state = StateReducer(graph, now=timestamp + timedelta(seconds=1)).reduce(history)
    assert state.history_size == 1
    assert state.nearby_entities[0].canonical_id == f"npc_{npc.npc_id}"
    assert any("no action planning" in item for item in state.reasoning)


def test_package_validation_detects_duplicate_alias_and_reference_conflicts(tmp_path):
    duplicate = _minimal_package(
        tmp_path / "duplicate",
        {"maps": [_entity("m1", "地图"), _entity("m1", "地图") ]},
    )
    duplicate_result = duplicate.validate()
    assert duplicate_result.valid is False
    assert duplicate_result.duplicate_id_count == 1

    conflict = _minimal_package(
        tmp_path / "conflict",
        {"maps": [_entity("m1", "同名"), _entity("m2", "同名")]},
    )
    conflict_result = conflict.validate()
    assert conflict_result.valid is False
    assert conflict_result.alias_conflict_count == 1

    missing = _minimal_package(
        tmp_path / "missing",
        {
            "maps": [_entity("m1", "地图")],
            "quests": [
                {
                    "quest_id": "q1",
                    "name": "任务",
                    "npc_ids": ["missing-npc"],
                    "item_ids": [],
                    "map_ids": [],
                    "monster_ids": [],
                    "provenance": _entity("x", "x")["provenance"],
                }
            ],
        },
    )
    assert missing.validate().missing_reference_count == 1


def test_package_validation_detects_invalid_relation_and_provenance(tmp_path):
    invalid_relation = _minimal_package(
        tmp_path / "relation",
        {
            "maps": [_entity("m1", "地图")],
            "relations": [
                {
                    "source": "map",
                    "source_id": "m1",
                    "target": "map",
                    "target_id": "m1",
                    "relation_type": "NOT_A_RELATION",
                }
            ],
        },
    )
    relation_result = invalid_relation.validate()
    assert relation_result.valid is False
    assert relation_result.invalid_relation_count == 1

    incomplete = _minimal_package(
        tmp_path / "provenance",
        {"maps": [_entity("m1", "地图")]},
    )
    incomplete.packet["maps"][0]["provenance"].pop("server_profile")
    # The in-memory mutation is intentional: it models a sanitized package
    # missing one required provenance field without rewriting the fixture.
    result = incomplete.validate()
    assert result.valid is False
    assert result.provenance_coverage == 0.0


def test_privacy_sanitizer_preserves_public_reference_and_redacts_paths():
    sanitized = sanitize_source_metadata(
        {
            "source_id": "mxdc-cn-community",
            "source_reference": "https://mxdc.dvg.cn/",
            "private_path": r"C:\Users\private\session.json",
        }
    )
    assert sanitized["source_reference"] == "https://mxdc.dvg.cn/"
    assert sanitized["private_path"] == "<REDACTED_PATH>"
    assert "C:\\Users\\private" not in json.dumps(sanitized)
