"""Knowledge Dataset 单测:JSON 加载 / 降级 / alias / reload / version / fusion。"""

import json

import pytest

from maple_agent.fusion import FusionService
from maple_agent.knowledge.dataset import load_dataset
from maple_agent.knowledge_graph import build_graph
from maple_agent.providers.knowledge import JsonKnowledgeProvider
from maple_agent.vision import Observation


def test_json_dataset_load():
    dataset = load_dataset()
    assert dataset.version == "v1"
    assert any(node.name == "射手村" for node in dataset.maps)
    assert any(node.name == "赫丽娜" for node in dataset.npcs)
    assert any(node.name == "绿水灵" and node.drops == [1] for node in dataset.monsters)
    assert any(node.name == "树液" for node in dataset.items)
    relation_types = {relation.relation_type.value for relation in dataset.relations}
    assert {"CONTAINS", "LOCATED_AT", "SPAWNS", "DROPS", "CONNECTED_TO"} <= relation_types


def test_invalid_dataset_degrades(tmp_path):
    (tmp_path / "maps.json").write_text("not-a-list", encoding="utf-8")
    (tmp_path / "dataset.json").write_text(
        json.dumps({"version": "v0"}), encoding="utf-8"
    )
    dataset = load_dataset(tmp_path)
    assert dataset.version == "v0"
    assert dataset.maps == []
    assert dataset.npcs == []


def test_provider_loads_dataset_and_version():
    provider = JsonKnowledgeProvider()
    provider.initialize()
    assert provider.dataset is not None
    assert provider.dataset_version() == "v1"


def test_provider_reload_keeps_dataset():
    provider = JsonKnowledgeProvider()
    provider.initialize()
    provider.reload()
    assert provider.dataset_version() == "v1"
    assert provider.dataset is not None


def test_dataset_alias_matching():
    provider = JsonKnowledgeProvider()
    provider.initialize()
    graph = build_graph(provider)
    assert graph.find_map("Henesys").name == "射手村"
    assert graph.find_npc("弓箭手教官").name == "赫丽娜"


def test_dataset_fusion_with_ocr_correction(tmp_path):
    provider = JsonKnowledgeProvider()
    provider.initialize()
    fusion = FusionService(
        provider,
        graph=build_graph(provider),
        sessions_dir=tmp_path / "sessions",
    )
    world = fusion.fuse(
        [
            Observation(
                element="ocr_text",
                type="text",
                raw_value="射手村1",
                normalized_value="射手村1",
                confidence=0.9,
                source="mock",
            )
        ],
        trace_id="trace-dataset-correction",
    )
    assert world.current_map is not None
    assert world.current_map.name == "射手村"
    assert world.confidence == pytest.approx(0.765)
    replay = json.loads(
        (
            tmp_path
            / "sessions"
            / "trace-dataset-correction"
            / "knowledge_match.json"
        ).read_text(encoding="utf-8")
    )
    assert replay["matched"] == "射手村"
    assert replay["dataset_version"] == "v1"
    assert replay["candidate_list"][0]["text"] == "射手村1"
    assert "射手村" in replay["ranking"]
