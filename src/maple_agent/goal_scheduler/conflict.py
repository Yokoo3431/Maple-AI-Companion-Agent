"""GoalConflictResolver:资源/依赖/截止冲突检测(只读)。"""

from __future__ import annotations

from datetime import UTC, datetime

from maple_agent.goal_scheduler.models import (
    ConflictResolution,
    GoalScheduleRecord,
)


class GoalConflictResolver:
    """检测多目标之间的资源 / 依赖 / 截止时间冲突。"""

    def detect(
        self,
        records: list[GoalScheduleRecord],
    ) -> list[ConflictResolution]:
        conflicts: list[ConflictResolution] = []
        self._resource_conflicts(records, conflicts)
        self._dependency_conflicts(records, conflicts)
        self._deadline_conflicts(records, conflicts)
        return conflicts

    @staticmethod
    def _resource_conflicts(
        records: list[GoalScheduleRecord],
        conflicts: list[ConflictResolution],
    ) -> None:
        for index, left in enumerate(records):
            for right in records[index + 1 :]:
                if left.resource_cost + right.resource_cost > 1.0:
                    conflicts.append(
                        ConflictResolution(
                            conflict_type="RESOURCE",
                            affected_goals=[left.goal_id, right.goal_id],
                            resolution="错开高资源目标,降低并行资源占用",
                        )
                    )

    @staticmethod
    def _dependency_conflicts(
        records: list[GoalScheduleRecord],
        conflicts: list[ConflictResolution],
    ) -> None:
        by_id = {record.goal_id: record for record in records}
        for record in records:
            dependency = record.dependency
            if dependency not in by_id:
                continue
            dep_record = by_id[dependency]
            if (
                dep_record.deadline is not None
                and record.deadline is not None
                and dep_record.deadline > record.deadline
            ):
                conflicts.append(
                    ConflictResolution(
                        conflict_type="DEPENDENCY",
                        affected_goals=[dependency, record.goal_id],
                        resolution="调整依赖目标顺序或放宽截止时间",
                    )
                )

    @staticmethod
    def _deadline_conflicts(
        records: list[GoalScheduleRecord],
        conflicts: list[ConflictResolution],
    ) -> None:
        now = datetime.now(UTC)
        for index, left in enumerate(records):
            for right in records[index + 1 :]:
                if left.deadline is None or right.deadline is None:
                    continue
                gap = abs(
                    (left.deadline - right.deadline).total_seconds()
                )
                left_urgent = (
                    left.deadline - now
                ).total_seconds() < 86400 * 2
                right_urgent = (
                    right.deadline - now
                ).total_seconds() < 86400 * 2
                if gap < 86400 and left_urgent and right_urgent:
                    conflicts.append(
                        ConflictResolution(
                            conflict_type="DEADLINE",
                            affected_goals=[left.goal_id, right.goal_id],
                            resolution="按优先级错开截止时间或拆分目标",
                        )
                    )
