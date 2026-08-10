"""GoalExperienceStore:目标级经验库,只读查询。"""

from __future__ import annotations

import json
from pathlib import Path

from maple_agent.architecture import TRACE_SCHEMA_VERSION
from maple_agent.goal_memory.models import (
    GoalExperienceRecord,
    OptimizedTaskGraph,
)
from maple_agent.task_planning.models import LongHorizonGoal


class GoalExperienceStore:
    """保存成功/失败目标经验与恢复历史,提供只读查询。"""

    def __init__(
        self,
        records: list[GoalExperienceRecord] | None = None,
    ) -> None:
        self._records: list[GoalExperienceRecord] = list(records or [])
        self._by_id = {
            record.experience_id: record for record in self._records
        }

    def add(self, record: GoalExperienceRecord) -> None:
        if record.experience_id in self._by_id:
            return
        self._records.append(record)
        self._by_id[record.experience_id] = record

    def add_many(self, records: list[GoalExperienceRecord]) -> None:
        for record in records:
            self.add(record)

    def get(self, experience_id: str) -> GoalExperienceRecord | None:
        return self._by_id.get(experience_id)

    def all(self) -> list[GoalExperienceRecord]:
        return list(self._records)

    def count(self) -> int:
        return len(self._records)

    def similar_goal(
        self,
        *,
        goal_type: str = "",
        description: str = "",
        limit: int = 5,
    ) -> list[GoalExperienceRecord]:
        """相似目标:类型匹配优先,描述关键词次之。"""
        scored: list[tuple[int, GoalExperienceRecord]] = []
        for record in self._records:
            score = 0
            if goal_type and record.goal_type == goal_type:
                score += 2
            if description and self._description_overlap(
                description,
                record.goal_description,
            ):
                score += 1
            if score > 0:
                scored.append((score, record))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [record for _, record in scored[:limit]]

    def similar_task_graph(
        self,
        *,
        task_ids: list[str] | None = None,
        limit: int = 5,
    ) -> list[GoalExperienceRecord]:
        """相似任务图:任务模式交集。"""
        task_ids = task_ids or []
        task_set = set(task_ids)
        scored: list[tuple[int, GoalExperienceRecord]] = []
        for record in self._records:
            overlap = len(task_set & set(record.task_pattern))
            if overlap > 0:
                scored.append((overlap, record))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [record for _, record in scored[:limit]]

    def successful_strategy(
        self,
        *,
        goal_type: str = "",
        limit: int = 5,
    ) -> list[GoalExperienceRecord]:
        """成功策略:成功记录(可选类型过滤)。"""
        matches = [
            record
            for record in self._records
            if record.success
            and (not goal_type or record.goal_type == goal_type)
        ]
        return matches[:limit]

    def recovery_history(
        self,
        *,
        limit: int = 5,
    ) -> list[GoalExperienceRecord]:
        """恢复历史:含失败点的记录。"""
        matches = [
            record
            for record in self._records
            if record.failed_points
        ]
        return matches[:limit]

    @staticmethod
    def _description_overlap(left: str, right: str) -> bool:
        if not left or not right:
            return False
        if left in right or right in left:
            return True

        def bigrams(text: str) -> set[str]:
            if len(text) < 2:
                return {text} if text else set()
            return {text[index : index + 2] for index in range(len(text) - 1)}

        return bool(bigrams(left) & bigrams(right))


def save_goal_memory_trace(
    sessions_dir: str | Path,
    trace_id: str,
    *,
    goal: LongHorizonGoal | None,
    retrieved: list[GoalExperienceRecord],
    similarity_score: float,
    optimization: OptimizedTaskGraph | None = None,
) -> None:
    """写入 goal_memory_trace.json(统一 Replay)。"""
    directory = Path(sessions_dir) / trace_id
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "goal": (
            goal.model_dump(mode="json") if goal is not None else None
        ),
        "retrieved_experience": [
            record.model_dump(mode="json") for record in retrieved
        ],
        "similarity_score": similarity_score,
        "optimization": (
            optimization.model_dump(mode="json")
            if optimization is not None
            else {}
        ),
    }
    (directory / "goal_memory_trace.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
