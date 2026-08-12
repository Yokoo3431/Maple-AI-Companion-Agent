"""ReflexStateDetector:融合/上下文 + HP/MP 信号 -> ReflexReference(只读)。"""

from __future__ import annotations

from maple_agent.logging_setup import new_id
from maple_agent.maple_context.models import MapleCompanionContextReference
from maple_agent.perception_fusion.models import PerceptionFusionReference
from maple_agent.reflex.event import DangerEventDetector
from maple_agent.reflex.models import (
    DangerEventType,
    HpMpReference,
    ReflexReference,
    ReflexStateType,
)
from maple_agent.reflex.threshold import ReflexThresholds


class ReflexStateDetector:
    """汇总 HP/MP/UI/危险事件,输出当前状态参考。"""

    def __init__(
        self,
        *,
        thresholds: ReflexThresholds | None = None,
        event_detector: DangerEventDetector | None = None,
    ) -> None:
        self.thresholds = thresholds or ReflexThresholds()
        self.event_detector = (
            event_detector or DangerEventDetector(self.thresholds)
        )
        self.last_reference: ReflexReference | None = None

    def detect(
        self,
        *,
        fusion_reference: PerceptionFusionReference | None = None,
        context_reference: MapleCompanionContextReference | None = None,
        hp_reference: HpMpReference | None = None,
        mp_reference: HpMpReference | None = None,
        death_signal: bool = False,
        status_effects: list[str] | None = None,
        ui_warnings: list[str] | None = None,
    ) -> ReflexReference:
        hp = hp_reference or self._hp_from_context(context_reference)
        mp = mp_reference or self._mp_from_context(context_reference)
        events = self.event_detector.detect(
            hp_reference=hp,
            mp_reference=mp,
            death_signal=death_signal,
            status_effects=status_effects,
            ui_warnings=ui_warnings,
        )
        event_types = {event.event_type for event in events}
        state = self._state(event_types, hp, mp)
        confidence = self._confidence(hp, mp, fusion_reference, state)
        reasoning = self._reasoning(hp, mp, events, state)
        reference = ReflexReference(
            reflex_id=new_id(),
            state=state,
            hp_reference=hp,
            mp_reference=mp,
            danger_events=events,
            ui_alerts=list(ui_warnings or []),
            confidence=confidence,
            reasoning=reasoning,
            validation="",
        )
        self.last_reference = reference
        return reference

    @staticmethod
    def _state(
        event_types: set[DangerEventType],
        hp: HpMpReference | None,
        mp: HpMpReference | None,
    ) -> ReflexStateType:
        if DangerEventType.DEATH in event_types:
            return ReflexStateType.DEATH
        if (
            DangerEventType.HP_LOW in event_types
            and DangerEventType.MP_LOW in event_types
        ):
            return ReflexStateType.DANGER
        if DangerEventType.HP_LOW in event_types:
            return ReflexStateType.LOW_HP
        if DangerEventType.MP_LOW in event_types:
            return ReflexStateType.LOW_MP
        if DangerEventType.STATUS_ABNORMAL in event_types:
            return ReflexStateType.DANGER
        if DangerEventType.UI_ALERT in event_types:
            return ReflexStateType.UI_ALERT
        if hp is not None or mp is not None:
            return ReflexStateType.NORMAL
        return ReflexStateType.UNKNOWN

    @staticmethod
    def _confidence(
        hp: HpMpReference | None,
        mp: HpMpReference | None,
        fusion: PerceptionFusionReference | None,
        state: ReflexStateType,
    ) -> float:
        known = sum(1 for item in (hp, mp) if item is not None)
        base = {2: 0.9, 1: 0.7, 0: 0.4}[known]
        if fusion is not None and fusion.fused_confidence < 0.5:
            base -= 0.1
        if state is ReflexStateType.UNKNOWN:
            base = min(base, 0.5)
        return round(min(1.0, max(0.0, base)), 4)

    @staticmethod
    def _reasoning(
        hp: HpMpReference | None,
        mp: HpMpReference | None,
        events,
        state: ReflexStateType,
    ) -> list[str]:
        reasoning: list[str] = []
        if hp is not None and hp.ratio is not None:
            reasoning.append(f"HP 比例: {hp.ratio}")
        if mp is not None and mp.ratio is not None:
            reasoning.append(f"MP 比例: {mp.ratio}")
        for event in events:
            reasoning.append(event.reasoning)
        reasoning.append(f"状态: {state.value}")
        return reasoning

    def _hp_from_context(
        self,
        context: MapleCompanionContextReference | None,
    ) -> HpMpReference | None:
        if context is None or context.player_context is None:
            return None
        value = context.player_context.current_hp_reference
        if value is None:
            return None
        maximum = self.thresholds.default_max_hp
        return HpMpReference(
            current_value=value,
            max_value=maximum,
            ratio=round(value / maximum, 4),
            confidence=context.player_context.confidence,
            source="context",
        )

    def _mp_from_context(
        self,
        context: MapleCompanionContextReference | None,
    ) -> HpMpReference | None:
        if context is None or context.player_context is None:
            return None
        value = context.player_context.current_mp_reference
        if value is None:
            return None
        maximum = self.thresholds.default_max_mp
        return HpMpReference(
            current_value=value,
            max_value=maximum,
            ratio=round(value / maximum, 4),
            confidence=context.player_context.confidence,
            source="context",
        )
