"""MultiGoalScheduler:多目标优先级调度(只读)。"""

from __future__ import annotations

import json
from pathlib import Path

from maple_agent.architecture import TRACE_SCHEMA_VERSION
from maple_agent.goal_scheduler.conflict import GoalConflictResolver
from maple_agent.goal_scheduler.models import (
    ConflictResolution,
    GoalPriorityResult,
    GoalScheduleRecord,
    OptimizedGoalSchedule,
)
from maple_agent.goal_scheduler.priority import GoalPriorityCalculator
from maple_agent.logging_setup import new_id
from maple_agent.task_planning.models import LongHorizonGoal


class MultiGoalScheduler:
    """输入多目标 + 规划质量 + 预防参考 -> 优化调度。"""

    def __init__(
        self,
        *,
        priority_calculator: GoalPriorityCalculator | None = None,
        conflict_resolver: GoalConflictResolver | None = None,
    ) -> None:
        self.priority_calculator = (
            priority_calculator or GoalPriorityCalculator()
        )
        self.conflict_resolver = conflict_resolver or GoalConflictResolver()
        self.last_priorities: list[GoalPriorityResult] = []
        self.last_conflicts: list[ConflictResolution] = []
        self.last_schedule: OptimizedGoalSchedule | None = None

    def schedule(
        self,
        *,
        goals: list[LongHorizonGoal],
        records: list[GoalScheduleRecord] | None = None,
        planning_quality: dict[str, float] | None = None,
        prevention_reference: dict[str, str] | None = None,
    ) -> OptimizedGoalSchedule:
        records = records or [
            self._record_from_goal(goal) for goal in goals
        ]
        priorities = {
            record.goal_id: self.priority_calculator.calculate(record)
            for record in records
        }
        conflicts = self.conflict_resolver.detect(records)
        ordered = self._order(records, priorities)
        selected = ordered[0] if ordered else ""
        deferred = ordered[1:] if len(ordered) > 1 else []
        reasoning = [f"最高优先级目标: {selected}"] if selected else []
        if conflicts:
            for conflict in conflicts:
                reasoning.append(
                    f"冲突[{conflict.conflict_type}]: "
                    f"{', '.join(conflict.affected_goals)}"
                )
        if planning_quality:
            for goal_id, score in sorted(planning_quality.items()):
                if score < 0.4:
                    reasoning.append(
                        f"{goal_id} 规划质量低({score:.2f}),"
                        "建议完善后再调度"
                    )
        if prevention_reference:
            for goal_id, summary in prevention_reference.items():
                if summary:
                    reasoning.append(f"{goal_id} 预防参考: {summary}")
        schedule = OptimizedGoalSchedule(
            goal_order=ordered,
            selected_goal=selected,
            deferred_goals=deferred,
            reasoning=reasoning,
            summary="; ".join(reasoning) or "无调度",
        )
        self.last_priorities = list(priorities.values())
        self.last_conflicts = conflicts
        self.last_schedule = schedule
        return schedule

    @staticmethod
    def _record_from_goal(goal: LongHorizonGoal) -> GoalScheduleRecord:
        return GoalScheduleRecord(
            schedule_id=new_id(),
            goal_id=goal.goal_id,
            priority=goal.priority,
            importance=round(goal.priority / 100, 4),
            urgency=0.5,
            resource_cost=0.3,
            confidence=0.6,
        )

    @staticmethod
    def _order(
        records: list[GoalScheduleRecord],
        priorities: dict[str, GoalPriorityResult],
    ) -> list[str]:
        sorted_records = sorted(
            records,
            key=lambda record: priorities[record.goal_id].score,
            reverse=True,
        )
        all_ids = {record.goal_id for record in records}
        ordered: list[str] = []
        placed: set[str] = set()
        for record in sorted_records:
            dependency = record.dependency
            if dependency in all_ids and dependency not in placed:
                dep_record = next(
                    item
                    for item in records
                    if item.goal_id == dependency
                )
                if dep_record.goal_id not in placed:
                    ordered.append(dep_record.goal_id)
                    placed.add(dep_record.goal_id)
            if record.goal_id not in placed:
                ordered.append(record.goal_id)
                placed.add(record.goal_id)
        return ordered


def save_goal_schedule_trace(
    sessions_dir: str | Path,
    trace_id: str,
    *,
    goals: list[LongHorizonGoal],
    priority_scores: list[GoalPriorityResult],
    schedule: OptimizedGoalSchedule,
    conflicts: list[ConflictResolution],
) -> None:
    """写入 goal_schedule_trace.json(统一 Replay)。"""
    directory = Path(sessions_dir) / trace_id
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "goals": [
            goal.model_dump(mode="json") for goal in goals
        ],
        "priority_scores": [
            score.model_dump(mode="json") for score in priority_scores
        ],
        "schedule": schedule.model_dump(mode="json"),
        "conflicts": [
            conflict.model_dump(mode="json") for conflict in conflicts
        ],
    }
    (directory / "goal_schedule_trace.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
