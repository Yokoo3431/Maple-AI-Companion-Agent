"""Long Horizon Planning 单测:目标 / 拆解 / 依赖 / recovery / replay / context / WebUI。"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from maple_agent.agent_loop.models import AgentLoopContext, AgentLoopStatus
from maple_agent.events import EventBus
from maple_agent.reflection.models import FailureType, ReflectionResult
from maple_agent.runtime import RuntimeManager
from maple_agent.task_planning import (
    LongHorizonGoal,
    LongHorizonValidator,
    Milestone,
    RecoveryAction,
    RecoveryPlanner,
    TaskDecomposer,
    TaskExecutionStateManager,
    TaskGraph,
    TaskNode,
    save_task_planning_trace,
)
from maple_agent.webui.app import create_app


def _goal() -> LongHorizonGoal:
    return LongHorizonGoal(
        goal_id="goal-1",
        description="完成新手任务链",
        priority=10,
        constraints=["只读观察", "Mock Only"],
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


def _reflection(failure_type: FailureType | None) -> ReflectionResult:
    return ReflectionResult(
        reflection_id="refl-1",
        execution_id="exec-1",
        success=failure_type is None,
        failure_type=failure_type,
        failure_reason="" if failure_type is None else "失败",
        confidence=0.6,
        next_action="continue" if failure_type is None else "replan",
        trace_id="trace-recovery",
    )


def test_goal_creation():
    goal = _goal()
    assert goal.goal_id == "goal-1"
    assert goal.description == "完成新手任务链"
    assert goal.priority == 10
    assert goal.success_condition == "提交任务并验证完成"
    assert len(goal.milestones) == 3
    assert goal.milestones[0].title == "找到 NPC"


def test_decomposition():
    graph = TaskDecomposer().decompose(_goal())
    assert graph.goal_id == "goal-1"
    assert len(graph.milestones) == 3
    assert len(graph.tasks) == 4
    first = graph.tasks[0]
    assert first.objective == "找到 NPC: task-1"
    assert first.prerequisite == ""
    assert first.expected_result == "完成 task-1"
    assert first.failure_condition == "task-1 执行失败"
    second = graph.tasks[1]
    assert second.prerequisite == "task-1"
    third = graph.tasks[2]
    assert third.prerequisite == "task-2"
    assert third.milestone_index == 2


def test_milestone_order_valid():
    graph = TaskDecomposer().decompose(_goal())
    result = LongHorizonValidator().validate(graph)
    assert result.valid is True
    assert result.issues == []


def test_milestone_order_invalid():
    goal = _goal().model_copy(
        update={
            "milestones": [
                _goal().milestones[1],
                _goal().milestones[0],
            ]
        }
    )
    graph = TaskDecomposer().decompose(goal)
    result = LongHorizonValidator().validate(graph)
    assert result.valid is False
    assert any("顺序非法" in issue for issue in result.issues)


def test_circular_dependency_detection():
    graph = TaskGraph(
        goal_id="goal-cycle",
        milestones=[],
        tasks=[
            task_node("task-1", prerequisite="task-2"),
            task_node("task-2", prerequisite="task-1"),
        ],
    )
    result = LongHorizonValidator().validate(graph)
    assert result.valid is False
    assert any("循环依赖" in issue for issue in result.issues)


def test_dependency_not_satisfied():
    graph = TaskDecomposer().decompose(_goal())
    manager = TaskExecutionStateManager(graph)
    # task-2 仍在 pending 且前置 task-1 未完成
    result = LongHorizonValidator().validate(
        graph,
        state=manager.snapshot(),
    )
    assert any(
        "前置任务未完成" in issue for issue in result.issues
    )


def test_state_manager_progress_and_next():
    graph = TaskDecomposer().decompose(_goal())
    manager = TaskExecutionStateManager(graph)
    assert manager.current_task().task_id == "task-1"
    manager.mark_completed("task-1")
    assert manager.current_task().task_id == "task-2"
    manager.mark_completed("task-2")
    assert manager.current_task().task_id == "task-3"
    assert manager.progress() == 0.5


def test_recovery_planning_mapping():
    planner = RecoveryPlanner()
    assert (
        planner.plan(_reflection(FailureType.EXECUTION_FAILED)).action
        is RecoveryAction.RETRY
    )
    assert (
        planner.plan(_reflection(FailureType.WORLD_MISMATCH)).action
        is RecoveryAction.RE_OBSERVATION
    )
    assert (
        planner.plan(_reflection(FailureType.KNOWLEDGE_ERROR)).action
        is RecoveryAction.KNOWLEDGE_REFRESH
    )
    assert (
        planner.plan(_reflection(FailureType.LOW_CONFIDENCE)).action
        is RecoveryAction.HUMAN_CONFIRMATION
    )
    assert (
        planner.plan(_reflection(None)).action is RecoveryAction.RETRY
    )


def test_replay_generation(tmp_path):
    goal = _goal()
    graph = TaskDecomposer().decompose(goal)
    manager = TaskExecutionStateManager(graph)
    manager.mark_completed("task-1")
    recovery = RecoveryPlanner().plan(
        _reflection(FailureType.EXECUTION_FAILED),
        goal_id=goal.goal_id,
        task_id="task-3",
    )
    save_task_planning_trace(
        tmp_path,
        "trace-replay",
        goal=goal,
        graph=graph,
        state=manager.snapshot(),
        recovery=recovery,
    )
    replay = json.loads(
        (tmp_path / "trace-replay" / "task_planning_trace.json").read_text(
            encoding="utf-8"
        )
    )
    assert replay["schema_version"] == "1.0"
    assert replay["goal_id"] == "goal-1"
    assert len(replay["milestones"]) == 3
    assert replay["current_task"] == "task-2"
    assert replay["progress"] == 0.25
    assert replay["recovery"][0]["action"] == "retry"
    assert "task_graph" in replay
    assert "state" in replay


def test_context_integration():
    goal = _goal()
    graph = TaskDecomposer().decompose(goal)
    manager = TaskExecutionStateManager(graph)
    context = AgentLoopContext(
        trace_id="trace-context",
        status=AgentLoopStatus.COMPLETED,
        goal_state=goal,
        task_graph=graph,
        planning_state=manager.snapshot(),
    )
    assert context.goal_state is not None
    assert context.goal_state.goal_id == "goal-1"
    assert context.task_graph is not None
    assert len(context.task_graph.tasks) == 4
    assert context.planning_state is not None
    assert context.planning_state.pending_tasks


def test_webui_long_horizon_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    goal = _goal()
    graph = TaskDecomposer().decompose(goal)
    manager = TaskExecutionStateManager(graph)
    manager.mark_completed("task-1")
    manager.mark_completed("task-2")
    recovery = RecoveryPlanner().plan(
        _reflection(FailureType.EXECUTION_FAILED),
        goal_id=goal.goal_id,
        task_id="task-3",
    )
    payload = {
        "goal": goal.model_dump(mode="json"),
        "graph": graph.model_dump(mode="json"),
        "state": manager.snapshot().model_dump(mode="json"),
        "recovery": recovery.model_dump(mode="json"),
        "progress": manager.progress(),
    }
    app = create_app(runtime=runtime, bus=bus, long_horizon=payload)
    with TestClient(app) as client:
        resp = client.get("/api/long-horizon/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is True
    assert data["goal"]["goal_id"] == "goal-1"
    assert data["state"]["next_action"] == "task-3"
    assert data["recovery"]["action"] == "retry"


def test_webui_long_horizon_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/long-horizon/state")
    assert resp.json()["enabled"] is False


def task_node(task_id: str, *, prerequisite: str = "") -> TaskNode:
    return TaskNode(
        task_id=task_id,
        objective=task_id,
        prerequisite=prerequisite,
        expected_result=f"完成 {task_id}",
        failure_condition=f"{task_id} 失败",
    )
