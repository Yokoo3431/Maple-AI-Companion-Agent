"""Maple Game Knowledge 单测:实体/关系/导入/图谱查询/检索/校验/replay/context/WebUI。"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from maple_agent.agent_loop.models import AgentLoopContext, AgentLoopStatus
from maple_agent.events import EventBus
from maple_agent.maple_context.models import (
    MapleCompanionContextReference,
    MapleWorldContext,
)
from maple_agent.maple_knowledge import (
    MapleKnowledgeEntity,
    MapleKnowledgeGraph,
    MapleKnowledgeRetriever,
    MapleKnowledgeType,
    MapleKnowledgeValidator,
    MapleKnowledgeVerdict,
    load_demo_knowledge,
    save_maple_knowledge_trace,
)
from maple_agent.maple_knowledge.models import KnowledgeRelationType
from maple_agent.maple_knowledge.relations import KnowledgeRelationBuilder
from maple_agent.runtime import RuntimeManager
from maple_agent.webui.app import create_app


def _entity(
    knowledge_id: str = "npc-1",
    *,
    knowledge_type: MapleKnowledgeType = MapleKnowledgeType.NPC,
    name: str = "赫丽娜",
    aliases: list[str] | None = None,
    description: str = "desc",
    confidence: float = 0.9,
) -> MapleKnowledgeEntity:
    return MapleKnowledgeEntity(
        knowledge_id=knowledge_id,
        knowledge_type=knowledge_type,
        name=name,
        aliases=aliases or [],
        description=description,
        source="test",
        confidence=confidence,
    )


def _graph():
    entities, relations = load_demo_knowledge()
    graph = MapleKnowledgeGraph()
    for entity in entities:
        graph.add_entity(entity)
    for relation in relations:
        graph.add_relation(relation)
    return graph, entities, relations


def _context() -> MapleCompanionContextReference:
    return MapleCompanionContextReference(
        world_context=MapleWorldContext(
            location="射手村",
            visible_entities=["赫丽娜"],
            confidence=0.9,
        ),
        confidence=0.9,
        trace_id="trace-knowledge",
    )


def test_entity_creation():
    entity = _entity()
    assert entity.knowledge_id == "npc-1"
    assert entity.knowledge_type is MapleKnowledgeType.NPC
    assert entity.name == "赫丽娜"
    assert entity.confidence == 0.9


def test_relation_creation():
    relation = KnowledgeRelationBuilder().build(
        source_id="monster-100",
        target_id="item-2000001",
        relation_type=KnowledgeRelationType.DROPS,
        confidence=0.8,
    )
    assert relation.source_id == "monster-100"
    assert relation.relation_type is KnowledgeRelationType.DROPS
    assert relation.confidence == 0.8


def test_import_demo_data():
    entities, relations = load_demo_knowledge()
    assert len(entities) == 9
    assert len(relations) == 7
    types = {entity.knowledge_type for entity in entities}
    assert MapleKnowledgeType.MAP in types
    assert MapleKnowledgeType.QUEST in types
    assert MapleKnowledgeType.SKILL in types


def test_graph_find_by_name_and_alias():
    graph, _, _ = _graph()
    assert graph.find_by_name("射手村") is not None
    assert graph.find_by_name("Henesys").name == "射手村"
    assert graph.find_by_name("不存在") is None


def test_graph_find_by_type():
    graph, _, _ = _graph()
    maps = graph.find_by_type(MapleKnowledgeType.MAP)
    assert len(maps) == 2
    assert {entity.name for entity in maps} == {"射手村", "魔法密林"}


def test_graph_find_related():
    graph, _, _ = _graph()
    related = graph.find_related("npc-101")
    assert related
    assert any(target.name == "射手村" for _, target in related)


def test_npc_lookup():
    graph, _, _ = _graph()
    npc = graph.find_by_name("赫丽娜")
    assert npc is not None
    assert npc.knowledge_type is MapleKnowledgeType.NPC
    assert npc.description == "弓箭手教官"


def test_monster_lookup():
    graph, _, _ = _graph()
    monster = graph.find_by_name("绿水灵")
    assert monster is not None
    assert monster.knowledge_type is MapleKnowledgeType.MONSTER


def test_item_relation():
    graph, _, _ = _graph()
    related = graph.find_related("monster-100")
    items = [
        target.name
        for relation, target in related
        if relation.relation_type is KnowledgeRelationType.DROPS
    ]
    assert items == ["蓝药水"]


def test_quest_relation():
    graph, _, _ = _graph()
    related = graph.find_related("quest-1")
    targets = {target.name for _, target in related}
    assert "赫丽娜" in targets
    assert "射手村" in targets
    types = {relation.relation_type for relation, _ in related}
    assert KnowledgeRelationType.REQUIRES in types
    assert KnowledgeRelationType.LOCATED_IN in types


def test_retrieval():
    graph, _, _ = _graph()
    retriever = MapleKnowledgeRetriever(graph)
    reference = retriever.retrieve(context=_context())
    assert "赫丽娜" in reference.related_npcs
    assert "射手村" in reference.related_maps
    assert "新手任务" in reference.related_quests
    assert reference.confidence > 0.8
    assert reference.reasoning


def test_retrieval_no_context():
    graph, _, _ = _graph()
    retriever = MapleKnowledgeRetriever(graph)
    reference = retriever.retrieve(context=None)
    assert reference.confidence == 0.0
    assert reference.related_maps == []


def test_validator_entity():
    validator = MapleKnowledgeValidator()
    valid = _entity()
    assert (
        validator.validate_entity(valid).verdict
        is MapleKnowledgeVerdict.VALID
    )
    no_desc = _entity(description="")
    assert (
        validator.validate_entity(no_desc).verdict
        is MapleKnowledgeVerdict.WARNING
    )
    invalid_type = _entity().model_copy(
        update={"knowledge_type": "UNKNOWN"}
    )
    assert (
        validator.validate_entity(invalid_type).verdict
        is MapleKnowledgeVerdict.BLOCKED
    )


def test_validator_relation():
    validator = MapleKnowledgeValidator()
    graph, _, _ = _graph()
    valid = graph.all_relations()[0]
    assert (
        validator.validate_relation(valid, graph).verdict
        is MapleKnowledgeVerdict.VALID
    )
    broken = KnowledgeRelationBuilder().build(
        source_id="missing-1",
        target_id="npc-101",
        relation_type=KnowledgeRelationType.LOCATED_IN,
    )
    assert (
        validator.validate_relation(broken, graph).verdict
        is MapleKnowledgeVerdict.BLOCKED
    )


def test_replay_generation(tmp_path):
    graph, entities, relations = _graph()
    retriever = MapleKnowledgeRetriever(graph)
    reference = retriever.retrieve(context=_context())
    save_maple_knowledge_trace(
        tmp_path,
        "trace-replay",
        knowledge_entities=entities,
        relations=relations,
        retrieval_result=reference,
        validation="VALID",
    )
    replay = json.loads(
        (tmp_path / "trace-replay" / "maple_knowledge_trace.json").read_text(
            encoding="utf-8"
        )
    )
    assert replay["schema_version"] == "1.0"
    assert len(replay["knowledge_entities"]) == 9
    assert len(replay["relations"]) == 7
    assert replay["retrieval_result"]["related_npcs"] == ["赫丽娜"]
    assert replay["validation"] == "VALID"


def test_agent_loop_integration():
    graph, _, _ = _graph()
    reference = MapleKnowledgeRetriever(graph).retrieve(context=_context())
    context = AgentLoopContext(
        trace_id="trace-maple",
        status=AgentLoopStatus.COMPLETED,
        maple_knowledge_reference=reference,
    )
    assert context.maple_knowledge_reference is not None
    assert "新手任务" in context.maple_knowledge_reference.related_quests


def test_webui_maple_knowledge_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    graph, entities, relations = _graph()
    retriever = MapleKnowledgeRetriever(graph)
    reference = retriever.retrieve(context=_context())
    payload = {
        "entity_count": len(entities),
        "categories": sorted(
            {entity.knowledge_type.value for entity in entities}
        ),
        "relation_count": len(relations),
        "retrieval": reference.model_dump(mode="json"),
        "validation": "VALID",
    }
    app = create_app(runtime=runtime, bus=bus, maple_knowledge=payload)
    with TestClient(app) as client:
        resp = client.get("/api/maple-knowledge/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is True
    assert data["entity_count"] == 9
    assert "MAP" in data["categories"]
    assert data["retrieval"]["related_npcs"] == ["赫丽娜"]


def test_webui_maple_knowledge_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/maple-knowledge/state")
    assert resp.json()["enabled"] is False
