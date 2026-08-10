"""Goal Memory 单测:经验 / 匹配 / 检索 / 优化 / replay / context / WebUI。"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from maple_agent.agent_loop.models import AgentLoopContext, AgentLoopStatus
from maple_agent.events import EventBus
from maple_agent.goal_memory import (
    GoalExperienceRecord,
    GoalExperienceRetriever,
    GoalExperienceStore,
    GoalMatcher,
    PlanningOptimizer,
    save_goal_memory_trace,
)
from maple_agent.runtime import RuntimeManager
from maple_agent.task_planning import (
    LongHorizonGoal,
    Milestone,
    TaskDecomposer,
)
from maple_agent.webui.app import create_app


def _goal() -> LongHorizonGoal:
    return LongHorizonGoal(
        goal_id="goal-1",
        description="完成新手任务链",
        priority=10,
        success_condition="提交任务并验证完成",
        milestones=[
            Milestone(
                milestone_id="ms-1",
                title="找到 NPC",
                order=0,
                task_ids=["task-1"],
            ),
            Milestone(
                milestone_id="ms-2",
                title="接受任务",
                order=1,
                task_ids=["task-2"],
            ),
            Milestone(
                milestone_id="ms-3",
                title="收集材料",
                order=2,
                task_ids=["task-3", "task-4"],
            ),
        ],
    )


def _graph():
    return TaskDecomposer().decompose(_goal())


def _experience(
    experience_id: str = "gxp-1",
    *,
    success: bool = True,
    failed_points: list[str] | None = None,
) -> GoalExperienceRecord:
    return GoalExperienceRecord(
        experience_id=experience_id,
        goal_type="QUEST",
        goal_description="完成新手任务链",
        successful_path=["task-1", "task-2", "task-3", "task-4"],
        failed_points=failed_points or [],
        task_pattern=["task-1", "task-2", "task-3", "task-4"],
        duration_estimate=600,
        success=success,
        confidence=0.9,
    )


def test_experience_create():
    record = _experience()
    assert record.experience_id == "gxp-1"
    assert record.goal_type == "QUEST"
    assert record.goal_description == "完成新手任务链"
    assert record.successful_path == [
        "task-1",
        "task-2",
        "task-3",
        "task-4",
    ]
    assert record.success is True
    assert record.confidence == 0.9


def test_goal_matching_high_score():
    matcher = GoalMatcher()
    match = matcher.score(
        experience=_experience(),
        current_goal=_goal(),
        task_graph=_graph(),
        goal_type="QUEST",
    )
    assert match.score > 0.7
    assert "目标类型匹配" in match.reasons
    assert "描述相似" in match.reasons
    assert "任务图相似" in match.reasons


def test_goal_matching_low_score():
    matcher = GoalMatcher()
    unrelated = GoalExperienceRecord(
        experience_id="gxp-x",
        goal_type="LEVELING",
        goal_description="提升等级到 30",
        successful_path=["task-x"],
        task_pattern=["task-x"],
    )
    match = matcher.score(
        experience=unrelated,
        current_goal=_goal(),
        task_graph=_graph(),
        goal_type="QUEST",
    )
    assert match.score < 0.3


def test_similarity_dimensions():
    matcher = GoalMatcher()
    record = _experience()
    # 仅目标类型匹配
    type_only = matcher.score(
        experience=record,
        goal_type="QUEST",
    )
    assert type_only.score == 0.3
    # 加上任务图匹配
    graph_match = matcher.score(
        experience=record,
        task_graph=_graph(),
        goal_type="QUEST",
    )
    assert graph_match.score > type_only.score


def test_successful_retrieval():
    store = GoalExperienceStore(
        [
            _experience("gxp-1", success=True),
            _experience("gxp-2", success=False, failed_points=["task-3"]),
        ]
    )
    strategies = store.successful_strategy(goal_type="QUEST")
    assert len(strategies) == 1
    assert strategies[0].success is True
    retriever = GoalExperienceRetriever(store)
    results = retriever.retrieve(
        current_goal=_goal(),
        task_graph=_graph(),
        goal_type="QUEST",
    )
    assert results
    assert results[0].experience_id == "gxp-1"
    assert retriever.last_best_score > 0.7


def test_failed_retrieval():
    store = GoalExperienceStore(
        [
            _experience("gxp-1", success=True),
            _experience("gxp-2", success=False, failed_points=["task-3"]),
        ]
    )
    history = store.recovery_history()
    assert len(history) == 1
    assert history[0].failed_points == ["task-3"]
    similar_failure = store.similar_goal(
        goal_type="QUEST",
        description="收集材料",
    )
    assert similar_failure


def test_graph_optimization():
    optimizer = PlanningOptimizer()
    failed_exp = _experience(
        "gxp-2",
        success=False,
        failed_points=["task-3"],
    )
    optimized = optimizer.optimize(graph=_graph(), experience=failed_exp)
    assert "task-3" in optimized.removed_tasks
    assert optimized.reordered is True
    assert optimized.recovery_hints
    assert any("历史失败点" in hint for hint in optimized.recovery_hints)
    assert optimized.graph is not None
    remaining = [task.task_id for task in optimized.graph.tasks]
    assert "task-3" not in remaining


def test_replay_generation(tmp_path):
    store = GoalExperienceStore([_experience()])
    retriever = GoalExperienceRetriever(store)
    retrieved = retriever.retrieve(
        current_goal=_goal(),
        task_graph=_graph(),
        goal_type="QUEST",
    )
    optimized = PlanningOptimizer().optimize(
        graph=_graph(),
        experience=retrieved[0] if retrieved else None,
    )
    save_goal_memory_trace(
        tmp_path,
        "trace-replay",
        goal=_goal(),
        retrieved=retrieved,
        similarity_score=retriever.last_best_score,
        optimization=optimized,
    )
    replay = json.loads(
        (tmp_path / "trace-replay" / "goal_memory_trace.json").read_text(
            encoding="utf-8"
        )
    )
    assert replay["schema_version"] == "1.0"
    assert replay["goal"]["goal_id"] == "goal-1"
    assert replay["retrieved_experience"][0]["experience_id"] == "gxp-1"
    assert replay["similarity_score"] > 0.7
    assert "optimization" in replay
    assert replay["optimization"]["recovery_hints"]


def test_context_integration():
    store = GoalExperienceStore([_experience()])
    retriever = GoalExperienceRetriever(store)
    retrieved = retriever.retrieve(
        current_goal=_goal(),
        task_graph=_graph(),
        goal_type="QUEST",
    )
    optimized = PlanningOptimizer().optimize(
        graph=_graph(),
        experience=retrieved[0] if retrieved else None,
    )
    context = AgentLoopContext(
        trace_id="trace-context",
        status=AgentLoopStatus.COMPLETED,
        goal_experience=retrieved[0] if retrieved else None,
        planning_reference=optimized,
    )
    assert context.goal_experience is not None
    assert context.goal_experience.experience_id == "gxp-1"
    assert context.planning_reference is not None
    assert context.planning_reference.summary


def test_webui_goal_memory_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    store = GoalExperienceStore([_experience()])
    retriever = GoalExperienceRetriever(store)
    retrieved = retriever.retrieve(
        current_goal=_goal(),
        task_graph=_graph(),
        goal_type="QUEST",
    )
    optimized = PlanningOptimizer().optimize(
        graph=_graph(),
        experience=retrieved[0] if retrieved else None,
    )
    payload = {
        "goal": _goal().model_dump(mode="json"),
        "retrieved": [
            record.model_dump(mode="json") for record in retrieved
        ],
        "similarity": retriever.last_best_score,
        "optimization": optimized.model_dump(mode="json"),
    }
    app = create_app(runtime=runtime, bus=bus, goal_memory=payload)
    with TestClient(app) as client:
        resp = client.get("/api/goal-memory/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is True
    assert data["goal"]["goal_id"] == "goal-1"
    assert data["retrieved"][0]["experience_id"] == "gxp-1"
    assert data["similarity"] > 0.7


def test_webui_goal_memory_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/goal-memory/state")
    assert resp.json()["enabled"] is False
