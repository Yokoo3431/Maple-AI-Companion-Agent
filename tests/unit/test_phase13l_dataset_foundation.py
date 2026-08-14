"""Phase 13-L versioned dataset and source adapter foundation tests."""

from __future__ import annotations

import json

from maple_agent.hybrid_vision import EvidenceResolver, PerceptionEvidence
from maple_agent.knowledge import load_dataset
from maple_agent.knowledge_quality import (
    KnowledgeCoverageDenominator,
    KnowledgeImportOrchestrator,
    KnowledgeReadinessPolicy,
    KnowledgeSourceReference,
    KnowledgeSourceType,
    LocalStaticKnowledgeAdapter,
    content_hash,
    sanitize_source_metadata,
    save_knowledge_acquisition_trace,
    write_versioned_dataset_record,
)
from maple_agent.maple_knowledge import (
    MapleKnowledgeBase,
    MapleKnowledgeGraph,
    load_phase13j_fixture,
)


def _graph() -> MapleKnowledgeGraph:
    entities, relations = load_phase13j_fixture()
    base = MapleKnowledgeBase()
    for entity in entities:
        base.add_entity(entity)
    for relation in relations:
        base.add_relation(relation)
    return MapleKnowledgeGraph(base)


def _source(path: str) -> KnowledgeSourceReference:
    return KnowledgeSourceReference(
        source_id="phase13l-fixture",
        source_type=KnowledgeSourceType.LOCAL_STATIC_FILE,
        source_name="sanitized fixture",
        source_reference=path,
        game_profile="maple-v113",
        server_profile="fixture-server",
        data_version="phase13l-v1",
    )


def _packet() -> dict:
    return {
        "maps": [
            {
                "map_id": "map-1",
                "name": "射手村",
                "aliases": ["Henesys"],
            }
        ],
        "npcs": [
            {
                "npc_id": "npc-1",
                "name": "赫丽娜",
                "aliases": ["Heena"],
            }
        ],
        "relations": [],
    }


def test_dataset_version_metadata_and_content_hash(tmp_path):
    packet = _packet()
    source_path = tmp_path / "public_fixture.json"
    source_path.write_text(json.dumps(packet, ensure_ascii=False), encoding="utf-8")
    source = _source(str(source_path))
    result = KnowledgeImportOrchestrator(
        policy=KnowledgeReadinessPolicy(minimum_total_entities=1)
    ).acquire(
        source,
        LocalStaticKnowledgeAdapter(),
        denominators=[
            KnowledgeCoverageDenominator(
                source_name="phase13l",
                expected_counts={"map": 1, "npc": 1},
            )
        ],
    )

    expected_hash = content_hash(packet)
    assert result.dataset is not None
    assert result.dataset.version == "phase13l-v1"
    assert result.dataset.game_profile == "maple-v113"
    assert result.dataset.server_profile == "fixture-server"
    assert result.dataset.source_provenance == ["phase13l-fixture"]
    assert result.dataset.content_hash == expected_hash
    assert result.manifest.content_hash == expected_hash
    assert result.dataset_metadata is not None
    assert result.dataset_metadata.dataset_version == "phase13l-v1"
    assert result.dataset_metadata.content_hash == expected_hash
    assert result.benchmark.entity_coverage == 1.0
    assert result.benchmark.alias_coverage == 1.0
    assert result.benchmark.missing_reference_count == 0


def test_existing_source_adapter_contract_has_explicit_metadata():
    adapter = LocalStaticKnowledgeAdapter()
    assert adapter.adapter_name == "LocalStaticKnowledgeAdapter"
    assert adapter.adapter_version == "1.0"
    assert callable(adapter.load)


def test_dataset_loader_reads_versioned_metadata_and_new_collections(tmp_path):
    (tmp_path / "dataset.json").write_text(
        json.dumps(
            {
                "dataset_version": "phase13l-v2",
                "game_profile": "maple-v113",
                "server_profile": "fixture-server",
                "source_provenance": ["source-a"],
                "content_hash": "hash-a",
            }
        ),
        encoding="utf-8",
    )
    (tmp_path / "equipment.json").write_text(
        json.dumps([{"equipment_id": "eq-1", "name": "测试短剑"}], ensure_ascii=False),
        encoding="utf-8",
    )
    (tmp_path / "quests.json").write_text(
        json.dumps([{"quest_id": "quest-1", "name": "测试任务"}], ensure_ascii=False),
        encoding="utf-8",
    )
    dataset = load_dataset(tmp_path)

    assert dataset.version == "phase13l-v2"
    assert dataset.game_profile == "maple-v113"
    assert dataset.server_profile == "fixture-server"
    assert dataset.source_provenance == ["source-a"]
    assert dataset.content_hash == "hash-a"
    assert len(dataset.equipment) == 1
    assert len(dataset.quests) == 1


def test_versioned_record_and_acquisition_trace_redact_private_paths(tmp_path):
    packet = _packet()
    source_path = tmp_path / "private_user_source.json"
    source_path.write_text(json.dumps(packet, ensure_ascii=False), encoding="utf-8")
    result = KnowledgeImportOrchestrator().acquire(
        _source(str(source_path)),
        LocalStaticKnowledgeAdapter(),
    )
    version_dir = write_versioned_dataset_record(result, str(tmp_path / "versions"))
    sources_path = tmp_path / "versions" / "phase13l-v1" / "sources.json"
    sources = json.loads(sources_path.read_text(encoding="utf-8"))
    assert sources["source_reference"] == "<REDACTED_PATH>"
    assert str(source_path) not in json.dumps(sources)
    assert (tmp_path / "versions" / "phase13l-v1" / "dataset_metadata.json").exists()
    assert "private_user_source" not in json.dumps(
        json.loads(
            (tmp_path / "versions" / "phase13l-v1" / "validation_report.json").read_text(
                encoding="utf-8"
            )
        )
    )
    assert version_dir.endswith("phase13l-v1")

    save_knowledge_acquisition_trace(
        tmp_path,
        "trace-13l",
        manifest=result.manifest.model_dump(mode="json"),
        sources=result.source.model_dump(mode="json"),
        import_summary={},
        mapping_summary={},
        conflicts=[],
        benchmark=result.benchmark,
        readiness=result.readiness.model_dump(mode="json"),
        validation=result.validation,
    )
    trace = json.loads(
        (tmp_path / "trace-13l" / "knowledge_acquisition_trace.json").read_text(
            encoding="utf-8"
        )
    )
    assert trace["sources"]["source_reference"] == "<REDACTED_PATH>"
    assert str(source_path) not in json.dumps(trace)


def test_source_metadata_sanitizer_preserves_public_identity_only(tmp_path):
    source = _source(str(tmp_path / "personal" / "source.json"))
    sanitized = sanitize_source_metadata(source)
    assert sanitized["source_id"] == "phase13l-fixture"
    assert sanitized["source_reference"] == "<REDACTED_PATH>"
    assert "personal" not in json.dumps(sanitized)


def test_phase13j_resolver_consumes_same_canonical_graph_after_dataset_work():
    result = EvidenceResolver().resolve(
        PerceptionEvidence(
            evidence_id="e-compat",
            evidence_type="npc",
            value="弓箭手教官",
            confidence=0.8,
        ),
        _graph(),
    )

    assert result.resolved is True
    assert result.selected is not None
    assert result.selected.canonical_id == "npc_heena"
