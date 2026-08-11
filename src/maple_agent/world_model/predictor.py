"""WorldStatePredictor:基于历史预测未来环境(仅参考,只读)。"""

from __future__ import annotations

from maple_agent.world_model.models import (
    EnvironmentHistory,
    PredictedEnvironmentState,
)


class WorldStatePredictor:
    """基于环境历史推断未来状态;禁止修改真实状态。"""

    def predict(
        self,
        *,
        history: EnvironmentHistory,
    ) -> PredictedEnvironmentState:
        if not history.snapshots:
            return PredictedEnvironmentState(
                confidence=0.0,
                reasoning=["无历史数据"],
                summary="无历史,无法预测",
            )
        entities: set[str] = set()
        resources: set[str] = set()
        locations = [
            snapshot.location
            for snapshot in history.snapshots
            if snapshot.location
        ]
        for snapshot in history.snapshots:
            entities.update(snapshot.visible_entities)
            resources.update(snapshot.resources)
        predicted_location = self._predict_location(
            locations,
            locations[-1] if locations else "",
        )
        reasoning = [
            f"基于 {len(history.snapshots)} 个环境快照",
            f"最近位置: {predicted_location or '未知'}",
            f"累计可见实体: {len(entities)}",
        ]
        confidence = self._confidence(history)
        return PredictedEnvironmentState(
            predicted_location=predicted_location,
            predicted_entities=sorted(entities),
            predicted_resources=sorted(resources),
            confidence=confidence,
            reasoning=reasoning,
            summary=(
                f"预测位于 {predicted_location or '未知'},"
                f"累计实体 {len(entities)} 个"
            ),
        )

    @staticmethod
    def _predict_location(
        locations: list[str],
        fallback: str,
    ) -> str:
        if len(locations) >= 3:
            # 简单规律: 若出现 A,B,A 模式, 预测回到 B
            if (
                locations[-1] == locations[-3]
                and locations[-2] != locations[-1]
            ):
                return locations[-2]
        return fallback

    @staticmethod
    def _confidence(history: EnvironmentHistory) -> float:
        if not history.snapshots:
            return 0.0
        average = (
            sum(snapshot.confidence for snapshot in history.snapshots)
            / len(history.snapshots)
        )
        return round(min(average, 0.9), 4)
