"""DangerEventDetector:危险事件检测(确定性规则,无 LLM)。"""

from __future__ import annotations

from maple_agent.logging_setup import new_id
from maple_agent.reflex.models import (
    DangerEventReference,
    DangerEventType,
    HpMpReference,
)
from maple_agent.reflex.threshold import ReflexThresholds


class DangerEventDetector:
    """检测 HP/MP/死亡/异常状态/UI 告警事件。"""

    def __init__(self, thresholds: ReflexThresholds | None = None) -> None:
        self.thresholds = thresholds or ReflexThresholds()
        self.last_events: list[DangerEventReference] = []

    def detect(
        self,
        *,
        hp_reference: HpMpReference | None = None,
        mp_reference: HpMpReference | None = None,
        death_signal: bool = False,
        status_effects: list[str] | None = None,
        ui_warnings: list[str] | None = None,
    ) -> list[DangerEventReference]:
        events: list[DangerEventReference] = []
        severity = self.thresholds.event_severity
        death = death_signal or (
            hp_reference is not None
            and hp_reference.ratio is not None
            and hp_reference.ratio <= 0
        )
        if death:
            events.append(
                DangerEventReference(
                    event_id=new_id(),
                    event_type=DangerEventType.DEATH,
                    severity=severity.get("DEATH", 1.0),
                    source=(
                        hp_reference.source
                        if hp_reference is not None
                        else "death_signal"
                    ),
                    confidence=(
                        hp_reference.confidence
                        if hp_reference is not None
                        else 0.9
                    ),
                    reasoning=(
                        "死亡信号或 HP 比例为 0"
                        if death_signal
                        else f"HP 比例 {hp_reference.ratio} 为 0"
                    ),
                )
            )
        else:
            if (
                hp_reference is not None
                and hp_reference.ratio is not None
                and hp_reference.ratio
                < self.thresholds.low_hp_threshold
            ):
                events.append(
                    DangerEventReference(
                        event_id=new_id(),
                        event_type=DangerEventType.HP_LOW,
                        severity=severity.get("HP_LOW", 0.6),
                        source=hp_reference.source,
                        confidence=hp_reference.confidence,
                        reasoning=(
                            f"HP 比例 {hp_reference.ratio} 低于阈值 "
                            f"{self.thresholds.low_hp_threshold}"
                        ),
                    )
                )
            if (
                mp_reference is not None
                and mp_reference.ratio is not None
                and mp_reference.ratio
                < self.thresholds.low_mp_threshold
            ):
                events.append(
                    DangerEventReference(
                        event_id=new_id(),
                        event_type=DangerEventType.MP_LOW,
                        severity=severity.get("MP_LOW", 0.5),
                        source=mp_reference.source,
                        confidence=mp_reference.confidence,
                        reasoning=(
                            f"MP 比例 {mp_reference.ratio} 低于阈值 "
                            f"{self.thresholds.low_mp_threshold}"
                        ),
                    )
                )
        for effect in status_effects or []:
            events.append(
                DangerEventReference(
                    event_id=new_id(),
                    event_type=DangerEventType.STATUS_ABNORMAL,
                    severity=severity.get("STATUS_ABNORMAL", 0.7),
                    source="status_effect",
                    confidence=0.8,
                    reasoning=f"检测到异常状态: {effect}",
                )
            )
        for warning in ui_warnings or []:
            events.append(
                DangerEventReference(
                    event_id=new_id(),
                    event_type=DangerEventType.UI_ALERT,
                    severity=severity.get("UI_ALERT", 0.6),
                    source="ui_warning",
                    confidence=0.7,
                    reasoning=f"UI 告警: {warning}",
                )
            )
        self.last_events = events
        return events
