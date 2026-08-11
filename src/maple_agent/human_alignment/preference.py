"""PreferenceMemory:用户偏好记忆(只读积累)。"""

from __future__ import annotations

from datetime import UTC, datetime

from maple_agent.human_alignment.models import PreferenceRecord
from maple_agent.logging_setup import new_id


class PreferenceMemory:
    """记录用户偏好:接受 / 拒绝 / 手动纠正。"""

    def __init__(self) -> None:
        self._records: list[PreferenceRecord] = []

    def record(
        self,
        *,
        option_id: str,
        action: str,
        reason: str = "",
        trace_id: str = "",
    ) -> PreferenceRecord:
        record = PreferenceRecord(
            record_id=new_id(),
            option_id=option_id,
            action=action,
            reason=reason,
            timestamp=datetime.now(UTC),
        )
        self._records.append(record)
        return record

    def accepted_option_ids(self) -> list[str]:
        return [
            record.option_id
            for record in self._records
            if record.action in ("accept", "correct")
        ]

    def rejected_option_ids(self) -> list[str]:
        return [
            record.option_id
            for record in self._records
            if record.action == "reject"
        ]

    def history(self) -> list[PreferenceRecord]:
        return list(self._records)

    def count(self) -> int:
        return len(self._records)

    def approval_rate(self) -> float:
        if not self._records:
            return 0.5
        accepted = sum(
            1
            for record in self._records
            if record.action in ("accept", "correct")
        )
        return round(accepted / len(self._records), 4)
