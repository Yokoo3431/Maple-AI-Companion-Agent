"""EnvironmentTransitionDetector:状态转换检测(只读)。"""

from __future__ import annotations

from maple_agent.environment.models import EnvironmentState
from maple_agent.world_model.models import EnvironmentTransition


class EnvironmentTransitionDetector:
    """比较前后环境状态,生成转换记录。"""

    def detect(
        self,
        *,
        before: EnvironmentState,
        after: EnvironmentState,
    ) -> EnvironmentTransition:
        changes = self._changes(before, after)
        return EnvironmentTransition(
            from_state=before,
            to_state=after,
            changes=changes,
            transition_type=self._transition_type(before, after),
            confidence=round(min(before.confidence, after.confidence), 4),
        )

    @staticmethod
    def _changes(
        before: EnvironmentState,
        after: EnvironmentState,
    ) -> list[str]:
        changes: list[str] = []
        if before.location != after.location:
            changes.append(
                f"location: {before.location or '-'} -> "
                f"{after.location or '-'}"
            )
        before_entities = set(before.visible_entities)
        after_entities = set(after.visible_entities)
        added = after_entities - before_entities
        removed = before_entities - after_entities
        if added:
            changes.append("实体新增: " + ", ".join(sorted(added)))
        if removed:
            changes.append("实体消失: " + ", ".join(sorted(removed)))
        if set(before.resources) != set(after.resources):
            changes.append(
                f"resources: {before.resources} -> {after.resources}"
            )
        if before.conditions != after.conditions:
            changes.append("conditions 变化")
        if not changes:
            changes.append("环境无变化")
        return changes

    @staticmethod
    def _transition_type(
        before: EnvironmentState,
        after: EnvironmentState,
    ) -> str:
        if before.location != after.location:
            return "location"
        if set(before.visible_entities) != set(after.visible_entities):
            return "entity"
        if set(before.resources) != set(after.resources):
            return "resource"
        if before.conditions != after.conditions:
            return "condition"
        return "none"
