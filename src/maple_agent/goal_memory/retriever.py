"""GoalExperienceRetriever:按当前目标检索历史经验(只读)。"""

from __future__ import annotations

from maple_agent.goal_memory.matcher import GoalMatcher
from maple_agent.goal_memory.models import GoalExperienceRecord
from maple_agent.goal_memory.store import GoalExperienceStore
from maple_agent.task_planning.models import LongHorizonGoal, TaskGraph


class GoalExperienceRetriever:
    """检索相似目标经验并按相似度排序。"""

    def __init__(
        self,
        store: GoalExperienceStore,
        matcher: GoalMatcher | None = None,
    ) -> None:
        self.store = store
        self.matcher = matcher or GoalMatcher()
        self.last_results: list[tuple[float, GoalExperienceRecord]] = []
        self.last_best_score: float = 0.0

    def retrieve(
        self,
        *,
        current_goal: LongHorizonGoal | None = None,
        task_graph: TaskGraph | None = None,
        goal_type: str = "",
        limit: int = 5,
    ) -> list[GoalExperienceRecord]:
        scored: list[tuple[float, GoalExperienceRecord]] = []
        for experience in self.store.all():
            match = self.matcher.score(
                experience=experience,
                current_goal=current_goal,
                task_graph=task_graph,
                goal_type=goal_type,
            )
            scored.append((match.score, experience))
        scored.sort(key=lambda item: item[0], reverse=True)
        self.last_results = scored[:limit]
        self.last_best_score = scored[0][0] if scored else 0.0
        return [record for _, record in scored[:limit]]

    def best_match(
        self,
        *,
        current_goal: LongHorizonGoal | None = None,
        task_graph: TaskGraph | None = None,
        goal_type: str = "",
    ) -> tuple[float, GoalExperienceRecord | None]:
        results = self.retrieve(
            current_goal=current_goal,
            task_graph=task_graph,
            goal_type=goal_type,
            limit=1,
        )
        if not results:
            return 0.0, None
        return self.last_best_score, results[0]
