"""Quest Reasoning 单测:模型/状态推断/需求分析/目标生成/依赖图/校验/replay/context/WebUI。"""

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
    load_demo_knowledge,
)
from maple_agent.maple_knowledge.models import MapleKnowledgeReference
from maple_agent.perception import (
    MaplePerceptionBinder,
    MaplePerceptionReference,
    MockVisionProvider,
)
from maple_agent.quest_reasoning import (
    GoalDependency,
    GoalReference,
    GoalType,
    QuestGoalReference,
    QuestPlanner,
    QuestProgressReference,
    QuestReasoningValidator,
    QuestReasoningVerdict,
    QuestReference,
    QuestStateType,
    save_quest_reasoning_trace,
)
from maple_agent.runtime import RuntimeManager
from maple_agent.webui.app import create_app


def _graph() -> MapleKnowledgeGraph:
    entities, relations = load_demo_knowledge()
    graph = MapleKnowledgeGraph()
    for entity in entities:
        graph.add_entity(entity)
    for relation in relations:
        graph.add_relation(relation)
    return graph


def _context(
    location: str = "射手村",
    visible: tuple[str, ...] = ("赫丽娜",),
) -> MapleCompanionContextReference:
    return MapleCompanionContextReference(
        world_context=MapleWorldContext(
            location=location,
            visible_entities=list(visible),
            confidence=0.9,
        ),
        confidence=0.9,
        trace_id="trace-quest",
    )


def _knowledge_ref(
    graph: MapleKnowledgeGraph,
    context: MapleCompanionContextReference,
) -> MapleKnowledgeReference:
    return MapleKnowledgeRetriever(graph).retrieve(context=context)


def _perception_ref(
    graph: MapleKnowledgeGraph,
    *,
    location: str = "射手村",
    visible: tuple[str, ...] = ("赫丽娜",),
    ui_state: str = "quest_available",
) -> MaplePerceptionReference:
    observation = MockVisionProvider(
        location=location,
        visible_entities=list(visible),
        ui_state=ui_state,
        confidence=0.9,
    ).capture()
    return MaplePerceptionBinder(knowledge=graph).bind(observation)


def _plan(graph: MapleKnowledgeGraph):
    context = _context()
    planner = QuestPlanner(graph)
    reference = planner.plan(
        context=context,
        knowledge_reference=_knowledge_ref(graph, context),
        perception_reference=_perception_ref(graph),
    )
    return planner, reference


def test_quest_model_creation():
    quest = QuestReference(
        quest_id="quest-1",
        quest_name="新手任务",
        requirements=["赫丽娜"],
        confidence=0.85,
    )
    assert quest.quest_id == "quest-1"
    assert quest.requirements == ["赫丽娜"]
    assert quest.confidence == 0.85
    assert QuestStateType.AVAILABLE.value == "AVAILABLE"
    assert GoalType.NPC_INTERACTION_REFERENCE.value == (
        "NPC_INTERACTION_REFERENCE"
    )


def test_quest_state_detection():
    graph = _graph()
    _, reference = _plan(graph)
    progress = reference.quest_progress[0]
    assert progress.quest_name == "新手任务"
    assert progress.state is QuestStateType.AVAILABLE
    assert "所需实体已检测到" in progress.reasoning


def test_requirement_analysis():
    graph = _graph()
    _, reference = _plan(graph)
    progress = reference.quest_progress[0]
    assert "赫丽娜" in progress.completed_requirements
    assert progress.pending_requirements == []
    quest = reference.active_quests[0]
    assert "赫丽娜" in quest.requirements


def test_npc_binding():
    graph = _graph()
    _, reference = _plan(graph)
    quest = reference.active_quests[0]
    assert "赫丽娜" in quest.related_entities
    assert quest.quest_name == "新手任务"


def test_goal_generation():
    graph = _graph()
    _, reference = _plan(graph)
    assert reference.recommended_goals
    goal = reference.recommended_goals[0]
    assert goal.goal_type is GoalType.NPC_INTERACTION_REFERENCE
    assert "赫丽娜" in goal.description
    assert goal.related_quest == "新手任务"
    assert reference.blocked_goals == []


def test_dependency_graph():
    graph = _graph()
    _, reference = _plan(graph)
    pairs = {
        (dep.goal_id, dep.depends_on, dep.dependency_type)
        for dep in reference.dependencies
    }
    assert ("quest:新手任务", "npc:赫丽娜", "NPC") in pairs
    assert ("quest:新手任务", "map:射手村", "MAP") in pairs
    assert ("npc:赫丽娜", "map:射手村", "LOCATION") in pairs


def test_confidence_calculation():
    graph = _graph()
    _, reference = _plan(graph)
    progress = reference.quest_progress[0]
    assert progress.progress_confidence == 0.9
    assert reference.confidence == 0.9
    assert 0 <= reference.confidence <= 1


def test_validator_valid():
    graph = _graph()
    _, reference = _plan(graph)
    result = QuestReasoningValidator().validate(reference)
    assert result.verdict is QuestReasoningVerdict.VALID
    assert result.issues == []


def test_validator_warning():
    graph = _graph()
    graph.add_entity(
        MapleKnowledgeEntity(
            knowledge_id="quest-x",
            knowledge_type=MapleKnowledgeType.QUEST,
            name="无需求任务",
            description="测试任务",
            source="test",
            confidence=0.6,
        )
    )
    context = _context()
    reference = QuestPlanner(graph).plan(
        context=context,
        knowledge_reference=MapleKnowledgeReference(
            related_quests=["无需求任务"],
            confidence=0.7,
        ),
        perception_reference=_perception_ref(graph, ui_state=""),
    )
    result = QuestReasoningValidator().validate(reference)
    assert result.verdict is QuestReasoningVerdict.WARNING
    assert any("unknown" in issue for issue in result.issues)
    assert any("incomplete requirements" in issue for issue in result.issues)


def test_blocked_state_detection():
    graph = _graph()
    context = _context(location="魔法密林", visible=("爱丽丝",))
    reference = QuestPlanner(graph).plan(
        context=context,
        knowledge_reference=MapleKnowledgeReference(
            related_quests=["新手任务"],
            related_maps=["魔法密林"],
            confidence=0.8,
        ),
        perception_reference=MaplePerceptionReference(
            observation_id="obs-blocked",
            visible_map="魔法密林",
            confidence=0.8,
        ),
    )
    assert reference.quest_progress[0].state is QuestStateType.BLOCKED
    assert reference.blocked_goals
    assert (
        reference.blocked_goals[0].goal_type
        is GoalType.EXPLORATION_REFERENCE
    )


def test_validator_blocked_impossible_dependency():
    reference = QuestGoalReference(
        active_quests=[
            QuestReference(
                quest_id="quest-1",
                quest_name="新手任务",
                requirements=["赫丽娜"],
                confidence=0.9,
            )
        ],
        quest_progress=[
            QuestProgressReference(
                quest_id="quest-1",
                quest_name="新手任务",
                state=QuestStateType.AVAILABLE,
                progress_confidence=0.9,
            )
        ],
        recommended_goals=[
            GoalReference(
                goal_id="goal-1",
                goal_type=GoalType.NPC_INTERACTION_REFERENCE,
                description="与赫丽娜交互",
                confidence=0.9,
            )
        ],
        dependencies=[
            GoalDependency(
                dependency_id="dep-1",
                goal_id="",
                depends_on="",
                dependency_type="",
            )
        ],
        confidence=0.9,
    )
    result = QuestReasoningValidator().validate(reference)
    assert result.verdict is QuestReasoningVerdict.BLOCKED
    assert "impossible dependency" in result.issues


def test_replay_generation(tmp_path):
    graph = _graph()
    planner, reference = _plan(graph)
    save_quest_reasoning_trace(
        tmp_path,
        "trace-replay",
        quests=reference.active_quests,
        progress=reference.quest_progress,
        goals=reference.recommended_goals + reference.blocked_goals,
        dependencies=reference.dependencies,
        validation="VALID",
    )
    replay = json.loads(
        (
            tmp_path / "trace-replay" / "quest_reasoning_trace.json"
        ).read_text(encoding="utf-8")
    )
    assert replay["schema_version"] == "1.0"
    assert replay["quests"][0]["quest_name"] == "新手任务"
    assert replay["progress"][0]["state"] == "AVAILABLE"
    assert replay["goals"]
    assert replay["dependencies"]
    assert replay["validation"] == "VALID"
    assert planner.last_reference is not None


def test_context_integration():
    graph = _graph()
    _, reference = _plan(graph)
    context = AgentLoopContext(
        trace_id="trace-quest",
        status=AgentLoopStatus.COMPLETED,
        quest_goal_reference=reference,
    )
    assert context.quest_goal_reference is not None
    assert context.quest_goal_reference.active_quests[0].quest_name == (
        "新手任务"
    )


def test_webui_quest_reasoning_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    graph = _graph()
    _, reference = _plan(graph)
    payload = {
        "active_quests": [
            quest.model_dump(mode="json")
            for quest in reference.active_quests
        ],
        "quest_progress": [
            progress.model_dump(mode="json")
            for progress in reference.quest_progress
        ],
        "recommended_goals": [
            goal.model_dump(mode="json")
            for goal in reference.recommended_goals
        ],
        "blocked_goals": [
            goal.model_dump(mode="json")
            for goal in reference.blocked_goals
        ],
        "dependencies": [
            dep.model_dump(mode="json") for dep in reference.dependencies
        ],
        "confidence": reference.confidence,
        "reasoning": reference.reasoning,
        "validation": "VALID",
    }
    app = create_app(runtime=runtime, bus=bus, quest_reasoning=payload)
    with TestClient(app) as client:
        resp = client.get("/api/quest-reasoning/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is True
    assert data["active_quests"][0]["quest_name"] == "新手任务"
    assert data["quest_progress"][0]["state"] == "AVAILABLE"
    assert data["recommended_goals"][0]["goal_type"] == (
        "NPC_INTERACTION_REFERENCE"
    )
    assert data["confidence"] == 0.9
    assert data["validation"] == "VALID"


def test_webui_quest_reasoning_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/quest-reasoning/state")
    assert resp.json()["enabled"] is False
