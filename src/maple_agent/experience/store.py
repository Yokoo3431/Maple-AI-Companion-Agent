"""ExperienceStore:结构化经验库,提供只读相似性查询。"""

from __future__ import annotations

from maple_agent.experience.models import ExperienceRecord


class ExperienceStore:
    """内存经验库;add 构建记录,查询接口只读。"""

    def __init__(self, records: list[ExperienceRecord] | None = None) -> None:
        self._records: list[ExperienceRecord] = list(records or [])
        self._by_id = {
            record.experience_id: record for record in self._records
        }

    def add(self, record: ExperienceRecord) -> None:
        if record.experience_id in self._by_id:
            return
        self._records.append(record)
        self._by_id[record.experience_id] = record

    def add_many(self, records: list[ExperienceRecord]) -> None:
        for record in records:
            self.add(record)

    def get(self, experience_id: str) -> ExperienceRecord | None:
        return self._by_id.get(experience_id)

    def all(self) -> list[ExperienceRecord]:
        return list(self._records)

    def count(self) -> int:
        return len(self._records)

    def similar_situation(
        self,
        *,
        map_name: str = "",
        action: str = "",
        limit: int = 5,
    ) -> list[ExperienceRecord]:
        """相似情境:地图匹配优先,动作匹配次之。"""
        scored: list[tuple[int, ExperienceRecord]] = []
        for record in self._records:
            score = 0
            if (
                map_name
                and record.context_snapshot.get("map_name") == map_name
            ):
                score += 2
            if action and record.action.upper() == action.upper():
                score += 1
            if score > 0:
                scored.append((score, record))
        scored.sort(key=lambda item: item[0], reverse=True)
        return [record for _, record in scored[:limit]]

    def similar_failure(
        self,
        *,
        failure_type: str = "",
        limit: int = 5,
    ) -> list[ExperienceRecord]:
        """相似失败:匹配失败类型(仅失败记录)。"""
        matches = [
            record
            for record in self._records
            if not record.success
            and (
                not failure_type
                or record.failure_type == failure_type
            )
        ]
        return matches[:limit]

    def successful_recovery(
        self,
        *,
        action: str = "",
        limit: int = 5,
    ) -> list[ExperienceRecord]:
        """成功恢复经验:成功记录(可选动作过滤)。"""
        matches = [
            record
            for record in self._records
            if record.success
            and (not action or record.action.upper() == action.upper())
        ]
        return matches[:limit]
