"""Quest Planner 单测:model / resolver / planner / validator / context / loop / replay / WebUI。"""

import json

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from maple_agent.agent import AgentLoop
from maple_agent.context import AgentContext, ContextBuilder, QuestPlanContext
from maple_agent.events import Event, EventBus, EventType
from maple_agent.goal import Goal, MockGoalProvider, RuleBasedGoalSelector
from maple_agent.planner import MockPlannerProvider, serialize_for_planner
from maple_agent.providers.knowledge import MockKnowledgeProvider
from maple_agent.quest_planner import (
    QuestPlan,
    QuestPlanAction,
    QuestPlanner,
    QuestPlanStep,
    QuestPlanValidationError,
    QuestPlanValidator,
    QuestResolver,
)
from maple_agent.runtime import RuntimeManager
from maple_agent.webui.app import create_app


def test_quest_plan_schema():
    step = QuestPlanStep(
        step_id="s1",
        action=QuestPlanAction.TALK,
        description="找 NPC",
        related_npc=101,
    )
    plan = QuestPlan(plan_id="p1", quest_id=1, title="新手教学", steps=[step])
    assert plan.steps[0].action is QuestPlanAction.TALK
    with pytest.raises(ValidationError):
        QuestPlan(plan_id="p2", quest_id=1, title="x", steps=[step], confidence=1.5)
    assert "PRESS_KEY" not in {action.name for action in QuestPlanAction}
    assert "CLICK" not in {action.name for action in QuestPlanAction}
    assert "MOVE_MOUSE" not in {action.name for action in QuestPlanAction}


def test_resolver_goal_to_quest():
    knowledge = MockKnowledgeProvider()
    knowledge.initialize()
    resolver = QuestResolver(knowledge)
    goal = Goal(
        goal_id="g1",
        goal_type="QUEST",
        title="新手教学",
        source="quest:1",
    )
    quest = resolver.resolve(goal)
    assert quest is not None
    assert quest.name == "新手教学"
    assert quest.npc_id == 101


def test_resolver_safe_degradation():
    knowledge = MockKnowledgeProvider()
    knowledge.initialize()
    resolver = QuestResolver(knowledge)
    assert resolver.resolve(None) is None
    unknown = Goal(goal_id="g2", goal_type="QUEST", title="不存在任务", source="quest:999")
    assert resolver.resolve(unknown) is None
    leveling = Goal(goal_id="g3", goal_type="LEVELING", title="升级")
    assert resolver.resolve(leveling) is None


def test_planner_quest_to_plan():
    knowledge = MockKnowledgeProvider()
    knowledge.initialize()
    planner = QuestPlanner(knowledge)
    quest = knowledge.get_quest(2)  # 收集树液
    plan = planner.plan(quest, goal_id="g1", trace_id="trace-qp")
    actions = [step.action for step in plan.steps]
    assert QuestPlanAction.MOVE_HINT in actions
    assert QuestPlanAction.TALK in actions
    assert QuestPlanAction.COLLECT in actions
    assert QuestPlanAction.DELIVER in actions
    assert QuestPlanAction.COMPLETE in actions
    assert plan.goal_id == "g1"
    assert plan.trace_id == "trace-qp"


def test_validator_rejects_physical_and_data_errors():
    validator = QuestPlanValidator()
    physical = QuestPlan(
        plan_id="p1",
        quest_id=1,
        title="x",
        steps=[
            QuestPlanStep(
                step_id="s1",
                action=QuestPlanAction.TALK,
                description="press key 进入游戏",
            )
        ],
    )
    with pytest.raises(QuestPlanValidationError, match="物理动作"):
        validator.validate(physical)
    with pytest.raises(QuestPlanValidationError, match="空"):
        validator.validate(QuestPlan(plan_id="p2", quest_id=1, title="x", steps=[]))

    knowledge = MockKnowledgeProvider()
    knowledge.initialize()
    quest = knowledge.get_quest(1)
    bad_monster = QuestPlan(
        plan_id="p3",
        quest_id=1,
        title="x",
        steps=[
            QuestPlanStep(
                step_id="s1",
                action=QuestPlanAction.DEFEAT,
                description="打怪",
                related_monster=99,
            )
        ],
    )
    with pytest.raises(QuestPlanValidationError, match="怪物不一致"):
        validator.validate(bad_monster, quest=quest)


def test_validator_accepts_valid_plan():
    knowledge = MockKnowledgeProvider()
    knowledge.initialize()
    quest = knowledge.get_quest(1)
    planner = QuestPlanner(knowledge)
    plan = planner.plan(quest, goal_id="g1")
    QuestPlanValidator().validate(plan, quest=quest)


def test_context_quest_plan_injection():
    plan = QuestPlan(plan_id="p1", quest_id=1, title="新手教学", steps=[])
    context = AgentContext(
        runtime_state="READY",
        quest_plan_context=QuestPlanContext(
            active_quest_plan=plan,
            current_step=1,
            plan_history=[plan],
        ),
    )
    assert context.quest_plan_context.active_quest_plan.title == "新手教学"
    assert context.world_state is None  # WorldState 不变


def test_planner_input_includes_quest_plan():
    plan = QuestPlan(plan_id="p1", quest_id=1, title="新手教学", steps=[])
    context = AgentContext(
        runtime_state="READY",
        quest_plan_context=QuestPlanContext(active_quest_plan=plan),
    )
    planner_input = serialize_for_planner(context)
    assert planner_input.quest_plan is plan


@pytest.mark.asyncio
async def test_loop_quest_planning_events_and_replay(tmp_path):
    bus = EventBus()
    events: list[Event] = []
    bus.subscribe(events.append)
    await bus.start()
    knowledge = MockKnowledgeProvider()
    knowledge.initialize()
    goal_provider = MockGoalProvider(
        goals=[
            Goal(
                goal_id="g1",
                goal_type="QUEST",
                title="新手教学",
                source="quest:1",
                priority=10,
            )
        ]
    )
    loop = AgentLoop(
        bus=bus,
        context_builder=ContextBuilder(knowledge),
        planner=MockPlannerProvider(),
        sessions_dir=tmp_path / "sessions",
        goal_provider=goal_provider,
        goal_selector=RuleBasedGoalSelector(),
        quest_resolver=QuestResolver(knowledge),
        quest_planner=QuestPlanner(knowledge),
        quest_plan_validator=QuestPlanValidator(),
    )
    loop.run_once(runtime_state="READY", trace_id="trace-qp-loop")
    await bus.wait_idle()
    assert loop.last_quest_plan is not None
    assert loop.last_quest_plan.title == "新手教学"
    assert loop.quest_plan_validation == "ok"
    event_types = {event.event_type for event in events}
    assert EventType.QUEST_PLAN_CREATED in event_types
    assert EventType.QUEST_PLAN_VALIDATED in event_types
    created_traces = {
        event.trace_id
        for event in events
        if event.event_type is EventType.QUEST_PLAN_CREATED
    }
    assert created_traces == {"trace-qp-loop"}
    replay = json.loads(
        (tmp_path / "sessions" / "trace-qp-loop" / "quest_plan.json").read_text(
            encoding="utf-8"
        )
    )
    assert replay["goal_id"] == "g1"
    assert replay["quest_id"] == 1
    assert replay["steps"]
    assert replay["validation_result"] == "ok"
    await bus.stop()


@pytest.mark.asyncio
async def test_loop_quest_plan_failed_event():
    class FailingQuestPlanner:
        def plan(self, *args, **kwargs):
            raise RuntimeError("quest plan boom")

    bus = EventBus()
    events: list[Event] = []
    bus.subscribe(events.append)
    await bus.start()
    knowledge = MockKnowledgeProvider()
    knowledge.initialize()
    goal_provider = MockGoalProvider(
        goals=[
            Goal(
                goal_id="g1",
                goal_type="QUEST",
                title="新手教学",
                source="quest:1",
                priority=10,
            )
        ]
    )
    loop = AgentLoop(
        bus=bus,
        context_builder=ContextBuilder(knowledge),
        planner=MockPlannerProvider(),
        goal_provider=goal_provider,
        goal_selector=RuleBasedGoalSelector(),
        quest_resolver=QuestResolver(knowledge),
        quest_planner=FailingQuestPlanner(),
    )
    plan = loop.run_once(runtime_state="READY", trace_id="trace-qp-fail")
    await bus.wait_idle()
    assert plan is not None  # 循环仍完成
    assert loop.quest_plan_validation == "failed"
    assert loop.last_quest_plan_error is not None
    failed = [
        event
        for event in events
        if event.event_type is EventType.QUEST_PLAN_FAILED
    ]
    assert failed and failed[0].trace_id == "trace-qp-fail"
    await bus.stop()


def test_webui_quest_plan_state_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    knowledge = MockKnowledgeProvider()
    knowledge.initialize()
    goal_provider = MockGoalProvider(
        goals=[
            Goal(
                goal_id="g1",
                goal_type="QUEST",
                title="新手教学",
                source="quest:1",
                priority=10,
            )
        ]
    )
    loop = AgentLoop(
        bus=bus,
        context_builder=ContextBuilder(knowledge),
        planner=MockPlannerProvider(),
        goal_provider=goal_provider,
        goal_selector=RuleBasedGoalSelector(),
        quest_resolver=QuestResolver(knowledge),
        quest_planner=QuestPlanner(knowledge),
    )
    loop.run_once(runtime_state="READY", trace_id="trace-qp-web")
    app = create_app(runtime=runtime, bus=bus, agent_loop=loop)
    with TestClient(app) as client:
        resp = client.get("/api/quest-plan/state")
    data = resp.json()
    assert data["enabled"] is True
    assert data["plan"]["title"] == "新手教学"
    assert len(data["plan"]["steps"]) >= 4
    assert data["validation"] == "ok"


def test_webui_quest_plan_state_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/quest-plan/state")
    assert resp.json()["enabled"] is False
