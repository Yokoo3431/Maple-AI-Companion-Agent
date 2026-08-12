"""VisionScheduler:事件驱动只读调度(Cheap First, Expensive On Demand)。"""

from __future__ import annotations

from datetime import UTC, datetime

from maple_agent.hybrid_vision.models import (
    ChangeResult,
    PerceptionMethod,
    PlannedVisionTask,
)


class VisionScheduler:
    """决定每个 ROI 在何时运行哪个方法。

    策略:
    - HP/MP: COLOR_GEOMETRY 每 tick(cheap,高频)
    - map: TEMPLATE/OCR 仅当 map ROI 变化
    - quest/dialog: OCR 仅当对应 ROI 变化
    - entity: 按配置频率(LOCAL_DETECTOR/TEMPLATE),不要求每帧
    """

    def __init__(
        self,
        *,
        hp_mp_method: PerceptionMethod = PerceptionMethod.COLOR_GEOMETRY,
        map_methods: tuple[PerceptionMethod, ...] = (
            PerceptionMethod.TEMPLATE,
            PerceptionMethod.OCR,
        ),
        quest_method: PerceptionMethod = PerceptionMethod.OCR,
        dialog_method: PerceptionMethod = PerceptionMethod.OCR,
        entity_method: PerceptionMethod = PerceptionMethod.TEMPLATE,
        entity_interval_s: float = 1.0,
        roi_change_threshold: float = 0.05,
    ) -> None:
        self.hp_mp_method = hp_mp_method
        self.map_methods = map_methods
        self.quest_method = quest_method
        self.dialog_method = dialog_method
        self.entity_method = entity_method
        self.entity_interval_s = entity_interval_s
        self.roi_change_threshold = roi_change_threshold
        self._last_run: dict[str, datetime] = {}
        self.skipped_ocr_count = 0

    def _mark(self, key: str) -> None:
        self._last_run[key] = datetime.now(UTC)

    def _last(self, key: str) -> datetime | None:
        return self._last_run.get(key)

    def _roi_changed(self, change: ChangeResult, roi: str) -> bool:
        score = change.roi_scores.get(roi, change.score)
        return score >= self.roi_change_threshold

    def plan(
        self,
        change: ChangeResult,
        *,
        hp_mp_roi_present: bool = True,
        map_roi_present: bool = True,
        quest_roi_present: bool = True,
        dialog_roi_present: bool = True,
        entity_roi_present: bool = False,
        now: datetime | None = None,
    ) -> list[PlannedVisionTask]:
        """基于变化结果产出本轮任务;无变化时跳过昂贵 OCR。"""
        now = now or datetime.now(UTC)
        tasks: list[PlannedVisionTask] = []
        if hp_mp_roi_present:
            tasks.append(
                PlannedVisionTask(
                    roi="hp_mp",
                    method=self.hp_mp_method,
                    reason="cheap per-tick geometry",
                    priority=0,
                )
            )
        if map_roi_present and self._roi_changed(change, "map_label"):
            for method in self.map_methods:
                tasks.append(
                    PlannedVisionTask(
                        roi="map_label",
                        method=method,
                        reason="map ROI changed",
                        priority=1,
                    )
                )
        elif map_roi_present:
            self.skipped_ocr_count += 1
        if quest_roi_present and self._roi_changed(change, "quest"):
            tasks.append(
                PlannedVisionTask(
                    roi="quest",
                    method=self.quest_method,
                    reason="quest ROI changed",
                    priority=1,
                )
            )
        if dialog_roi_present and self._roi_changed(change, "dialog"):
            tasks.append(
                PlannedVisionTask(
                    roi="dialog",
                    method=self.dialog_method,
                    reason="dialog ROI changed",
                    priority=1,
                )
            )
        if entity_roi_present:
            last = self._last("entity")
            if last is None or (
                now - last
            ).total_seconds() >= self.entity_interval_s:
                tasks.append(
                    PlannedVisionTask(
                        roi="entity",
                        method=self.entity_method,
                        reason="entity scheduled frequency",
                        priority=2,
                    )
                )
                self._mark("entity")
        return tasks
