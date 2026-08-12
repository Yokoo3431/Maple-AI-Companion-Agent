"""Game State 单测:玩家/地图/实体/任务解析/校验/replay/context/WebUI。"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from maple_agent.agent_loop.models import AgentLoopContext, AgentLoopStatus
from maple_agent.events import EventBus
from maple_agent.game_state import (
    EntityStateParser,
    GameStateExtractor,
    GameStateValidator,
    GameStateVerdict,
    MapStateParser,
    PlayerStateParser,
    QuestStateParser,
    save_game_state_trace,
)
from maple_agent.maple_knowledge import (
    MapleKnowledgeEntity,
    MapleKnowledgeGraph,
    MapleKnowledgeType,
    load_demo_knowledge,
)
from maple_agent.maple_knowledge.models import KnowledgeRelation, KnowledgeRelationType
from maple_agent.runtime import RuntimeManager
from maple_agent.vision_runtime.models import ScreenObservation
from maple_agent.webui.app import create_app


def _graph() -> MapleKnowledgeGraph:
    entities, relations = load_demo_knowledge()
    graph = MapleKnowledgeGraph()
    for entity in entities:
        graph.add_entity(entity)
    for relation in relations:
        graph.add_relation(relation)
    return graph


def _observation(
    *,
    map_name: str = "射手村",
    entities: tuple[str, ...] = ("赫丽娜", "绿水灵", "红药水"),
    ui: tuple[str, ...] = ("任务提示",),
    hp: float | None = 0.8,
    mp: float | None = 0.6,
    quests: tuple[str, ...] = ("新手任务",),
    confidence: float = 0.9,
) -> ScreenObservation:
    return ScreenObservation(
        visible_map=map_name,
        visible_entities=list(entities),
        ui_elements=list(ui),
        hp_reference=hp,
        mp_reference=mp,
        quest_reference=list(quests),
        confidence=confidence,
    )


def _extract(graph: MapleKnowledgeGraph, observation: ScreenObservation):
    extractor = GameStateExtractor(graph)
    reference = extractor.extract(observation)
    validation = GameStateValidator().validate(reference)
    return reference, validation


def test_player_parser():
    player = PlayerStateParser().parse(_observation())
    assert player.hp == 0.8
    assert player.mp == 0.6
    assert player.level_reference is None
    assert player.job_reference == ""
    assert player.position_reference == {}


def test_map_parser_known():
    graph = _graph()
    known = MapStateParser(graph).parse(_observation())
    assert known.map_name == "射手村"
    assert known.known_map is True
    unknown = MapStateParser(graph).parse(
        _observation(map_name="未知地图")
    )
    assert unknown.known_map is False


def test_entity_parser():
    graph = _graph()
    entities = EntityStateParser(graph).parse(_observation())
    types = {entity.name: entity.type for entity in entities}
    assert types["赫丽娜"] == "NPC"
    assert types["绿水灵"] == "MONSTER"
    assert types["红药水"] == "ITEM"
    unknown = EntityStateParser(graph).parse(
        _observation(entities=("未知NPC",))
    )
    assert unknown[0].type == "UNKNOWN"


def test_quest_parser_active_and_available():
    graph = _graph()
    graph.add_entity(
        MapleKnowledgeEntity(
            knowledge_id="quest-2",
            knowledge_type=MapleKnowledgeType.QUEST,
            name="第二任务",
            description="测试任务",
            source="test",
            confidence=0.8,
        )
    )
    npc = graph.find_by_name("赫丽娜")
    quest = graph.find_by_name("第二任务")
    graph.add_relation(
        KnowledgeRelation(
            relation_id="r2",
            source_id=quest.knowledge_id,
            target_id=npc.knowledge_id,
            relation_type=KnowledgeRelationType.REQUIRES,
            confidence=0.8,
        )
    )
    snapshot = QuestStateParser(graph).parse(_observation())
    assert snapshot.active_quests == ["新手任务"]
    assert "第二任务" in snapshot.available_quests
    assert snapshot.completed_reference == []


def test_extractor_full():
    graph = _graph()
    reference, validation = _extract(graph, _observation())
    assert reference.state_id
    assert reference.player_state is not None
    assert reference.player_state.hp == 0.8
    assert reference.current_map is not None
    assert reference.current_map.known_map is True
    assert len(reference.visible_entities) == 3
    assert reference.quest_state is not None
    assert reference.quest_state.active_quests == ["新手任务"]
    assert reference.combat_state == "ENCOUNTER"
    assert reference.confidence == 0.9
    assert validation.verdict is GameStateVerdict.VALID


def test_combat_state_rules():
    graph = _graph()
    normal = GameStateExtractor(graph).extract(
        _observation(entities=("赫丽娜",))
    )
    assert normal.combat_state == "NORMAL"
    combat = GameStateExtractor(graph).extract(
        _observation(ui=("战斗中",), entities=("赫丽娜",))
    )
    assert combat.combat_state == "IN_COMBAT"


def test_validator_warning_missing_hp_mp():
    graph = _graph()
    reference, validation = _extract(
        graph,
        _observation(hp=None, mp=None),
    )
    assert validation.verdict is GameStateVerdict.WARNING
    assert any("missing hp/mp" in issue for issue in validation.issues)


def test_validator_warning_unknown_map():
    graph = _graph()
    reference, validation = _extract(
        graph,
        _observation(map_name="未知地图"),
    )
    assert validation.verdict is GameStateVerdict.WARNING
    assert any("unknown map" in issue for issue in validation.issues)


def test_validator_blocked():
    graph = _graph()
    extractor = GameStateExtractor(graph)
    reference = extractor.extract(_observation())
    malformed = reference.model_copy(update={"state_id": ""})
    validation = GameStateValidator().validate(malformed)
    assert validation.verdict is GameStateVerdict.BLOCKED
    assert "missing state id" in validation.issues


def test_replay_generation(tmp_path):
    graph = _graph()
    reference, validation = _extract(graph, _observation())
    save_game_state_trace(
        tmp_path,
        "trace-replay",
        player_state=reference.player_state,
        map_state=reference.current_map,
        entities=reference.visible_entities,
        quest_state=reference.quest_state,
        validation=validation.verdict.value,
    )
    replay = json.loads(
        (tmp_path / "trace-replay" / "game_state_trace.json").read_text(
            encoding="utf-8"
        )
    )
    assert replay["schema_version"] == "1.0"
    assert replay["player_state"]["hp"] == 0.8
    assert replay["map_state"]["map_name"] == "射手村"
    assert replay["map_state"]["known_map"] is True
    assert replay["entities"][0]["name"] == "赫丽娜"
    assert replay["quest_state"]["active_quests"] == ["新手任务"]
    assert replay["validation"] == "VALID"


def test_agent_loop_integration():
    graph = _graph()
    reference, _ = _extract(graph, _observation())
    context = AgentLoopContext(
        trace_id="trace-game-state",
        status=AgentLoopStatus.OBSERVING,
        game_state_reference=reference,
    )
    assert context.game_state_reference is not None
    assert context.game_state_reference.current_map.map_name == "射手村"
    assert context.game_state_reference.player_state.hp == 0.8


def test_webui_game_state_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    graph = _graph()
    reference, validation = _extract(graph, _observation())
    payload = {
        "state_id": reference.state_id,
        "player_state": (
            reference.player_state.model_dump(mode="json")
            if reference.player_state is not None
            else {}
        ),
        "current_map": (
            reference.current_map.model_dump(mode="json")
            if reference.current_map is not None
            else {}
        ),
        "visible_entities": [
            entity.model_dump(mode="json")
            for entity in reference.visible_entities
        ],
        "quest_state": (
            reference.quest_state.model_dump(mode="json")
            if reference.quest_state is not None
            else {}
        ),
        "combat_state": reference.combat_state,
        "confidence": reference.confidence,
        "reasoning": reference.reasoning,
        "validation": validation.verdict.value,
    }
    app = create_app(runtime=runtime, bus=bus, game_state=payload)
    with TestClient(app) as client:
        resp = client.get("/api/game-state/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is True
    assert data["current_map"]["map_name"] == "射手村"
    assert data["player_state"]["hp"] == 0.8
    assert data["visible_entities"][0]["name"] == "赫丽娜"
    assert data["quest_state"]["active_quests"] == ["新手任务"]
    assert data["validation"] == "VALID"


def test_webui_game_state_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/game-state/state")
    assert resp.json()["enabled"] is False
