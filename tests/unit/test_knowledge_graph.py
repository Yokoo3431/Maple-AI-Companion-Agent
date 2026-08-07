"""Knowledge Graph 单测:alias / map / npc / relation / fusion / replay / context。"""

import json

from maple_agent.context import ContextBuilder
from maple_agent.fusion import FusionService
from maple_agent.knowledge_graph import KnowledgeGraph, build_graph
from maple_agent.providers.knowledge import MockKnowledgeProvider
from maple_agent.vision import Observation


def _graph() -> KnowledgeGraph:
    knowledge = MockKnowledgeProvider()
    knowledge.initialize()
    return build_graph(knowledge)


def test_alias_matching():
    graph = _graph()
    assert graph.find_map("Henesys").name == "射手村"
    assert graph.find_map(1).name == "射手村"
    assert graph.find_map("不存在的地图") is None


def test_map_query():
    graph = _graph()
    node = graph.find_map(2)
    assert node.name == "勇士部落"
    assert node.aliases == ["Perion"]
    assert node.parent_region == "冒险岛世界"


def test_npc_query():
    graph = _graph()
    assert graph.find_npc(101).name == "赫丽娜"
    assert graph.find_npc("赫丽娜").npc_id == 101
    assert graph.find_npc(999) is None


def test_relation_query():
    graph = _graph()
    assert [npc.name for npc in graph.npcs_in_map(1)] == ["赫丽娜"]
    assert [monster.name for monster in graph.monsters_in_map(1)] == ["绿水灵"]
    relations = graph.relations_for("map", 1)
    assert any(relation.relation_type.value == "CONTAINS" for relation in relations)
    assert any(relation.relation_type.value == "SPAWNS" for relation in relations)


def test_fusion_success_with_graph(tmp_path):
    knowledge = MockKnowledgeProvider()
    knowledge.initialize()
    fusion = FusionService(
        knowledge,
        graph=build_graph(knowledge),
        sessions_dir=tmp_path / "sessions",
    )
    world = fusion.fuse(
        [
            Observation(
                element="ocr_text",
                type="text",
                raw_value="Henesys",
                normalized_value="Henesys",
                confidence=0.9,
                source="mock",
            )
        ],
        trace_id="trace-kg-ok",
    )
    assert world.current_map.name == "射手村"
    assert [npc.name for npc in world.known_npcs] == ["赫丽娜"]
    assert [monster.name for monster in world.known_monsters] == ["绿水灵"]
    assert world.confidence == 0.9
    replay = json.loads(
        (
            tmp_path
            / "sessions"
            / "trace-kg-ok"
            / "knowledge_match.json"
        ).read_text(encoding="utf-8")
    )
    assert replay["ocr_text"] == "Henesys"
    assert replay["matched"] == "射手村"
    assert replay["confidence"] == 0.9


def test_fusion_failure_with_graph(tmp_path):
    knowledge = MockKnowledgeProvider()
    knowledge.initialize()
    fusion = FusionService(
        knowledge,
        graph=build_graph(knowledge),
        sessions_dir=tmp_path / "sessions",
    )
    world = fusion.fuse(
        [
            Observation(
                element="ocr_text",
                type="text",
                raw_value="未知文本",
                normalized_value="未知文本",
                confidence=0.7,
                source="mock",
            )
        ],
        trace_id="trace-kg-fail",
    )
    assert world.current_map is None
    assert world.known_npcs == []
    assert world.known_monsters == []
    assert world.confidence == 0.0
    assert not (tmp_path / "sessions" / "trace-kg-fail" / "knowledge_match.json").exists()


def test_context_knowledge_state():
    knowledge = MockKnowledgeProvider()
    knowledge.initialize()
    fusion = FusionService(knowledge, graph=build_graph(knowledge))
    world = fusion.fuse(
        [
            Observation(
                element="ocr_text",
                type="text",
                raw_value="射手村",
                normalized_value="射手村",
                confidence=0.95,
                source="mock",
            )
        ],
        trace_id="trace-kg-ctx",
    )
    context = ContextBuilder(knowledge).build(
        vision_state=None,
        world_state=world,
        runtime_state="READY",
        trace_id="trace-kg-ctx",
    )
    assert context.knowledge_state is not None
    types = {entity.entity_type for entity in context.knowledge_state.matched_entities}
    assert types == {"map", "npc", "monster"}
    assert context.knowledge_state.confidence == 0.95
    assert context.knowledge_state.source == "knowledge_graph"
    assert context.world_state is not None  # WorldState 保留
