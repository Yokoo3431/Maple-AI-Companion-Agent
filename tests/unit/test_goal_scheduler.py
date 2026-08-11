"""Multi Goal Scheduling 单测:优先级 / 排序 / 冲突 / 调度 / replay / context / WebUI。"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient

from maple_agent.agent_loop.models import AgentLoopContext, AgentLoopStatus
from maple_agent.events import EventBus
from maple_agent.goal_scheduler import (
    GoalConflictResolver,
    GoalPriorityCalculator,
    GoalScheduleRecord,
    MultiGoalScheduler,
    save_goal_schedule_trace,
)
from maple_agent.runtime import RuntimeManager
from maple_agent.task_planning import LongHorizonGoal, Milestone
from maple_agent.webui.app import create_app


def _record(
    goal_id: str,
    *,
    importance: float = 0.5,
    urgency: float = 0.5,
    resource_cost: float = 0.3,
    dependency: str = "",
    deadline_days: int | None = None,
    confidence: float = 0.6,
) -> GoalScheduleRecord:
    return GoalScheduleRecord(
        schedule_id=f"sch-{goal_id}",
        goal_id=goal_id,
        priority=5,
        importance=importance,
        urgency=urgency,
        resource_cost=resource_cost,
        dependency=dependency,
        deadline=(
            datetime.now(UTC) + timedelta(days=deadline_days)
            if deadline_days is not None
            else None
        ),
        confidence=confidence,
    )


def _goal(goal_id: str = "goal-1", priority: int = 10) -> LongHorizonGoal:
    return LongHorizonGoal(
        goal_id=goal_id,
        description=goal_id,
        priority=priority,
        success_condition="完成",
        milestones=[
            Milestone(
                milestone_id=f"ms-{goal_id}",
                title=goal_id,
                order=0,
                task_ids=[f"task-{goal_id}"],
            )
        ],
    )


def test_goal_priority_formula():
    calculator = GoalPriorityCalculator()
    result = calculator.calculate(
        _record(
            "g1",
            importance=0.8,
            urgency=0.4,
            resource_cost=0.2,
            confidence=0.7,
        )
    )
    # 0.35*0.8 + 0.25*0.4 + 0.2*0.7 + 0.2*0.8 = 0.68
    assert result.score == 0.68
    assert result.goal_id == "g1"
    assert result.components["importance"] == 0.8
    assert result.reasoning


def test_urgency_with_deadline():
    calculator = GoalPriorityCalculator()
    urgent = calculator.calculate(
        _record("g-urgent", deadline_days=0)
    )
    assert urgent.components["urgency"] == 1.0
    no_deadline = calculator.calculate(_record("g-none"))
    assert no_deadline.components["urgency"] == 0.5


def test_multi_goal_ordering():
    records = [
        _record(
            "g1",
            importance=0.9,
            urgency=0.3,
            resource_cost=0.4,
            confidence=0.8,
        ),
        _record(
            "g2",
            importance=0.7,
            urgency=0.7,
            resource_cost=0.7,
            confidence=0.6,
        ),
        _record(
            "g3",
            importance=0.4,
            urgency=0.5,
            resource_cost=0.3,
            confidence=0.5,
        ),
    ]
    scheduler = MultiGoalScheduler()
    schedule = scheduler.schedule(
        goals=[_goal("g1"), _goal("g2"), _goal("g3")],
        records=records,
    )
    assert schedule.goal_order == ["g1", "g2", "g3"]
    assert schedule.selected_goal == "g1"
    assert schedule.deferred_goals == ["g2", "g3"]


def test_dependency_ordering():
    records = [
        _record("dep", importance=0.4, confidence=0.4),
        _record(
            "main",
            importance=0.9,
            confidence=0.9,
            dependency="dep",
        ),
    ]
    scheduler = MultiGoalScheduler()
    schedule = scheduler.schedule(
        goals=[_goal("main"), _goal("dep")],
        records=records,
    )
    assert schedule.goal_order == ["dep", "main"]
    assert schedule.goal_order.index("dep") < schedule.goal_order.index(
        "main"
    )


def test_resource_conflict_detection():
    resolver = GoalConflictResolver()
    conflicts = resolver.detect(
        [
            _record("g1", resource_cost=0.7),
            _record("g2", resource_cost=0.5),
        ]
    )
    assert any(
        conflict.conflict_type == "RESOURCE"
        for conflict in conflicts
    )


def test_dependency_deadline_conflict():
    resolver = GoalConflictResolver()
    conflicts = resolver.detect(
        [
            _record("g1", deadline_days=5),
            _record("g2", deadline_days=1, dependency="g1"),
        ]
    )
    assert any(
        conflict.conflict_type == "DEPENDENCY"
        for conflict in conflicts
    )


def test_deadline_conflict():
    resolver = GoalConflictResolver()
    conflicts = resolver.detect(
        [
            _record("g1", deadline_days=1),
            _record("g2", deadline_days=1),
        ]
    )
    assert any(
        conflict.conflict_type == "DEADLINE"
        for conflict in conflicts
    )


def test_schedule_generation_with_conflicts():
    records = [
        _record(
            "g1",
            importance=0.9,
            resource_cost=0.7,
            deadline_days=5,
        ),
        _record(
            "g2",
            importance=0.7,
            resource_cost=0.5,
            dependency="g1",
            deadline_days=1,
        ),
    ]
    scheduler = MultiGoalScheduler()
    schedule = scheduler.schedule(
        goals=[_goal("g1"), _goal("g2")],
        records=records,
    )
    assert schedule.goal_order == ["g1", "g2"]
    assert scheduler.last_conflicts
    assert any("冲突" in reason for reason in schedule.reasoning)
    assert schedule.summary


def test_replay_generation(tmp_path):
    scheduler = MultiGoalScheduler()
    goals = [_goal("g1"), _goal("g2")]
    records = [
        _record("g1", importance=0.9, confidence=0.8),
        _record(
            "g2",
            importance=0.7,
            confidence=0.6,
            dependency="g1",
        ),
    ]
    schedule = scheduler.schedule(goals=goals, records=records)
    save_goal_schedule_trace(
        tmp_path,
        "trace-replay",
        goals=goals,
        priority_scores=scheduler.last_priorities,
        schedule=schedule,
        conflicts=scheduler.last_conflicts,
    )
    replay = json.loads(
        (tmp_path / "trace-replay" / "goal_schedule_trace.json").read_text(
            encoding="utf-8"
        )
    )
    assert replay["schema_version"] == "1.0"
    assert len(replay["goals"]) == 2
    assert len(replay["priority_scores"]) == 2
    assert replay["schedule"]["selected_goal"] == "g1"
    assert isinstance(replay["conflicts"], list)


def test_context_integration():
    scheduler = MultiGoalScheduler()
    schedule = scheduler.schedule(
        goals=[_goal("g1"), _goal("g2")],
        records=[
            _record("g1", importance=0.9),
            _record("g2", importance=0.7),
        ],
    )
    context = AgentLoopContext(
        trace_id="trace-context",
        status=AgentLoopStatus.COMPLETED,
        goal_schedule=schedule,
        priority_reference=scheduler.last_priorities,
    )
    assert context.goal_schedule is not None
    assert context.goal_schedule.selected_goal == "g1"
    assert len(context.priority_reference) == 2
    assert context.priority_reference[0].goal_id == "g1"


def test_webui_goal_scheduler_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    scheduler = MultiGoalScheduler()
    goals = [_goal("g1"), _goal("g2")]
    schedule = scheduler.schedule(
        goals=goals,
        records=[
            _record("g1", importance=0.9, resource_cost=0.7),
            _record(
                "g2",
                importance=0.7,
                resource_cost=0.5,
                dependency="g1",
                deadline_days=1,
            ),
        ],
    )
    payload = {
        "goal_count": 2,
        "priority_scores": [
            score.model_dump(mode="json")
            for score in scheduler.last_priorities
        ],
        "schedule": schedule.model_dump(mode="json"),
        "conflicts": [
            conflict.model_dump(mode="json")
            for conflict in scheduler.last_conflicts
        ],
    }
    app = create_app(runtime=runtime, bus=bus, goal_scheduler=payload)
    with TestClient(app) as client:
        resp = client.get("/api/goal-scheduler/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is True
    assert data["goal_count"] == 2
    assert data["schedule"]["selected_goal"] == "g1"
    assert data["conflicts"]


def test_webui_goal_scheduler_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/goal-scheduler/state")
    assert resp.json()["enabled"] is False
