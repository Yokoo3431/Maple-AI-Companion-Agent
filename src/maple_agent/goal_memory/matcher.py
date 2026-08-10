"""GoalMatcher:当前目标 vs 历史经验 相似度评分(只读)。"""

from __future__ import annotations

from maple_agent.goal_memory.models import (
    GoalExperienceRecord,
    GoalMatchResult,
)
from maple_agent.task_planning.models import LongHorizonGoal, TaskGraph


class GoalMatcher:
    """评分维度:目标类型 / 描述 / 里程碑 / 任务图。"""

    def score(
        self,
        *,
        experience: GoalExperienceRecord,
        current_goal: LongHorizonGoal | None = None,
        task_graph: TaskGraph | None = None,
        goal_type: str = "",
    ) -> GoalMatchResult:
        score = 0.0
        reasons: list[str] = []
        if goal_type and experience.goal_type:
            if goal_type == experience.goal_type:
                score += 0.3
                reasons.append("目标类型匹配")
        if current_goal is not None and experience.goal_description:
            sim = self._text_similarity(
                current_goal.description,
                experience.goal_description,
            )
            score += 0.25 * sim
            if sim > 0:
                reasons.append("描述相似")
        if current_goal is not None:
            current_titles = {
                milestone.title for milestone in current_goal.milestones
            }
            path_set = set(experience.successful_path)
            if current_titles and path_set:
                ratio = len(current_titles & path_set) / len(current_titles)
                score += 0.25 * ratio
                if ratio > 0:
                    reasons.append("里程碑相似")
        if task_graph is not None:
            task_ids = {task.task_id for task in task_graph.tasks}
            pattern_set = set(experience.task_pattern)
            if task_ids and pattern_set:
                ratio = len(task_ids & pattern_set) / len(task_ids)
                score += 0.2 * ratio
                if ratio > 0:
                    reasons.append("任务图相似")
        return GoalMatchResult(
            experience_id=experience.experience_id,
            score=round(max(0.0, min(1.0, score)), 4),
            reasons=reasons,
        )

    @staticmethod
    def _text_similarity(left: str, right: str) -> float:
        def bigrams(text: str) -> set[str]:
            if len(text) < 2:
                return {text} if text else set()
            return {text[index : index + 2] for index in range(len(text) - 1)}

        left_tokens = bigrams(left)
        if not left_tokens:
            return 0.0
        right_tokens = bigrams(right)
        hits = len(left_tokens & right_tokens)
        return round(hits / len(left_tokens), 4)
