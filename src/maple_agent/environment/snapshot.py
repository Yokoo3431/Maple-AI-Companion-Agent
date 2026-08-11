"""EnvironmentSnapshotManager:记录环境变化(只读)。"""

from __future__ import annotations

from maple_agent.environment.models import EnvironmentSnapshot, EnvironmentState


class EnvironmentSnapshotManager:
    """捕获 before/after 环境状态并生成变化列表。"""

    def __init__(self) -> None:
        self.last_snapshot: EnvironmentSnapshot | None = None

    def capture(
        self,
        *,
        before: EnvironmentState | None,
        after: EnvironmentState,
        trace_id: str = "",
    ) -> EnvironmentSnapshot:
        changes = (
            self._diff(before, after)
            if before is not None
            else ["首次环境观察"]
        )
        snapshot = EnvironmentSnapshot(
            before_state=before,
            after_state=after,
            changes=changes,
            trace_id=trace_id,
        )
        self.last_snapshot = snapshot
        return snapshot

    @staticmethod
    def _diff(
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
        if before.confidence != after.confidence:
            changes.append(
                f"confidence: {before.confidence} -> {after.confidence}"
            )
        if not changes:
            changes.append("环境无变化")
        return changes
