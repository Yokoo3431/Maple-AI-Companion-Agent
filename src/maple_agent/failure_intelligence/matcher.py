"""FailurePatternMatcher:当前任务图/上下文 vs 历史失败模式(只读)。"""

from __future__ import annotations

from maple_agent.failure_intelligence.models import (
    FailureMatchResult,
    FailurePatternRecord,
)
from maple_agent.task_planning.models import TaskGraph


class FailurePatternMatcher:
    """FailureMatchScore = 0.3*Context + 0.3*Task + 0.2*Type + 0.2*Frequency。"""

    def score(
        self,
        *,
        pattern: FailurePatternRecord,
        current_task_graph: TaskGraph | None = None,
        current_context: dict | None = None,
        failure_type: str = "",
    ) -> FailureMatchResult:
        score = 0.0
        reasons: list[str] = []
        context_score = self._context_score(
            pattern.context_snapshot,
            current_context,
        )
        score += 0.3 * context_score
        if context_score > 0:
            reasons.append("上下文相似")
        task_score = self._task_score(
            pattern.affected_tasks,
            current_task_graph,
        )
        score += 0.3 * task_score
        if task_score > 0:
            reasons.append("任务相似")
        if failure_type and pattern.failure_type == failure_type:
            score += 0.2
            reasons.append("失败类型匹配")
        score += 0.2 * pattern.confidence
        return FailureMatchResult(
            pattern_id=pattern.pattern_id,
            score=round(max(0.0, min(1.0, score)), 4),
            reasons=reasons,
        )

    def match(
        self,
        *,
        patterns: list[FailurePatternRecord],
        current_task_graph: TaskGraph | None = None,
        current_context: dict | None = None,
        failure_type: str = "",
        limit: int = 5,
    ) -> list[FailureMatchResult]:
        scored = [
            self.score(
                pattern=pattern,
                current_task_graph=current_task_graph,
                current_context=current_context,
                failure_type=failure_type,
            )
            for pattern in patterns
        ]
        scored.sort(key=lambda item: item.score, reverse=True)
        return scored[:limit]

    @staticmethod
    def _context_score(
        snapshot: dict,
        current: dict | None,
    ) -> float:
        if not current:
            return 0.0
        hits = 0
        for key, value in snapshot.items():
            if key in current and current[key] == value:
                hits += 1
        return round(hits / max(1, len(snapshot)), 4)

    @staticmethod
    def _task_score(
        affected: list[str],
        current_task_graph: TaskGraph | None,
    ) -> float:
        if current_task_graph is None or not affected:
            return 0.0
        task_ids = {task.task_id for task in current_task_graph.tasks}
        if not task_ids:
            return 0.0
        overlap = len(task_ids & set(affected))
        return round(overlap / len(task_ids), 4)
