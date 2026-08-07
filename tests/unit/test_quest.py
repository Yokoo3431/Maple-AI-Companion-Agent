"""Quest Knowledge 单测:schema / graph / provider / context / replay / WebUI。"""

import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from maple_agent.agent import AgentLoop
from maple_agent.context import ContextBuilder
from maple_agent.events import EventBus
from maple_agent.logging_setup import setup_logging
from maple_agent.planner import MockPlannerProvider
from maple_agent.providers.knowledge import MockKnowledgeProvider
from maple_agent.quest import QuestGraph
from maple_agent.quest.models import Quest, QuestObjective, QuestReward
from maple_agent.runtime import RuntimeManager
from maple_agent.webui.app import create_app


def test_quest_schema_validation():
    quest = Quest(
        quest_id=1,
        name="新手教学",
        npc_id=101,
        map_id=1,
        monster_ids=[100],
        item_ids=[1],
        prerequisites=[0],
        objectives=[QuestObjective(objective_id="o1", kind="talk", target="101")],
        rewards=[QuestReward(kind="exp", target="10")],
    )
    assert quest.npc_id == 101
    with pytest.raises(ValidationError):
        Quest(quest_id=1)  # 缺少 name


def _sample_quests() -> list[Quest]:
    return [
        Quest(quest_id=1, name="新手教学", npc_id=101, map_id=1, monster_ids=[100], item_ids=[1]),
        Quest(
            quest_id=2,
            name="收集树液",
            npc_id=101,
            map_id=1,
            monster_ids=[100],
            item_ids=[2],
            prerequisites=[1],
        ),
        Quest(quest_id=3, name="前往勇士部落", npc_id=201, map_id=2),
    ]


def test_quest_graph_relations():
    graph = QuestGraph(_sample_quests())
    assert graph.get(1).name == "新手教学"
    assert [quest.name for quest in graph.prerequisites_of(2)] == ["新手教学"]
    assert [quest.name for quest in graph.by_npc(101)] == ["新手教学", "收集树液"]
    assert [quest.name for quest in graph.by_map(2)] == ["前往勇士部落"]
    assert [quest.name for quest in graph.by_monster(100)] == ["新手教学", "收集树液"]
    assert [quest.name for quest in graph.by_item(2)] == ["收集树液"]


def test_quest_graph_available():
    graph = QuestGraph(_sample_quests())
    assert [quest.name for quest in graph.available()] == ["新手教学", "前往勇士部落"]
    assert [quest.name for quest in graph.available([1])] == [
        "新手教学",
        "收集树液",
        "前往勇士部落",
    ]


def test_knowledge_provider_quest_queries():
    knowledge = MockKnowledgeProvider()
    knowledge.initialize()
    assert knowledge.get_quest(1).name == "新手教学"
    assert [quest.name for quest in knowledge.get_available_quests()] == ["新手教学"]
    assert [quest.name for quest in knowledge.get_available_quests([1])] == [
        "新手教学",
        "收集树液",
    ]
    assert knowledge.get_quest(999) is None


def test_context_goal_context_not_polluting_world_state():
    knowledge = MockKnowledgeProvider()
    knowledge.initialize()
    builder = ContextBuilder(knowledge)
    context = builder.build(
        vision_state=None,
        world_state=None,
        runtime_state="READY",
        trace_id="trace-quest-ctx",
    )
    assert context.goal_context is not None
    assert [quest.name for quest in context.goal_context.available_quests] == ["新手教学"]
    assert context.world_state is None  # WorldState 未被污染


def test_quest_trace_in_logs(tmp_path):
    setup_logging(tmp_path / "logs", level="INFO", console=False)
    knowledge = MockKnowledgeProvider()
    knowledge.initialize()
    knowledge.get_quest(1, trace_id="trace-quest-log")
    log = (tmp_path / "logs" / "startup.log").read_text(encoding="utf-8")
    assert "knowledge lookup: get_quest" in log
    assert "trace=trace-quest-log" in log


def test_loop_replay_quest_context(tmp_path):
    bus = EventBus()
    knowledge = MockKnowledgeProvider()
    knowledge.initialize()
    loop = AgentLoop(
        bus=bus,
        context_builder=ContextBuilder(knowledge),
        planner=MockPlannerProvider(),
        sessions_dir=tmp_path / "sessions",
    )
    loop.run_once(runtime_state="READY", trace_id="trace-quest-replay")
    replay_dir = tmp_path / "sessions" / "trace-quest-replay"
    assert (replay_dir / "agent_loop.json").exists()
    assert (replay_dir / "quest_context.json").exists()
    data = json.loads((replay_dir / "quest_context.json").read_text(encoding="utf-8"))
    assert data["available_quests"][0]["name"] == "新手教学"


def test_webui_quest_state_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    knowledge = MockKnowledgeProvider()
    knowledge.initialize()
    app = create_app(runtime=runtime, bus=bus, knowledge=knowledge)
    with TestClient(app) as client:
        resp = client.get("/api/quest/state")
    data = resp.json()
    assert data["enabled"] is True
    assert data["quest_total"] == 2
    assert data["available_total"] == 1


def test_webui_quest_state_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/quest/state")
    assert resp.json()["enabled"] is False
