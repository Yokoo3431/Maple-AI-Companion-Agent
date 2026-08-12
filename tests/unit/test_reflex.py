"""L1 Reflex 单测:模型/状态检测/危险事件/校验/replay/context/WebUI。"""

from __future__ import annotations

import json

from fastapi.testclient import TestClient

from maple_agent.agent_loop.models import AgentLoopContext, AgentLoopStatus
from maple_agent.events import EventBus
from maple_agent.maple_context.models import (
    MapleCompanionContextReference,
    MaplePlayerContext,
)
from maple_agent.reflex import (
    DangerEventDetector,
    DangerEventType,
    HpMpReference,
    ReflexReference,
    ReflexStateDetector,
    ReflexStateType,
    ReflexThresholds,
    ReflexValidator,
    ReflexVerdict,
    save_reflex_trace,
)
from maple_agent.runtime import RuntimeManager
from maple_agent.webui.app import create_app


def _hp(
    ratio: float | None = None,
    *,
    value: int | None = None,
    maximum: int = 1000,
) -> HpMpReference | None:
    if ratio is None and value is None:
        return None
    current = value if value is not None else (
        int(ratio * maximum) if ratio is not None else None
    )
    return HpMpReference(
        current_value=current,
        max_value=maximum,
        ratio=ratio,
        confidence=0.9,
        source="mock",
    )


def _mp(ratio: float | None = None) -> HpMpReference | None:
    return _hp(ratio)


def _detect(
    *,
    hp_ratio: float | None = None,
    mp_ratio: float | None = None,
    death: bool = False,
    status: list[str] | None = None,
    ui: list[str] | None = None,
    thresholds: ReflexThresholds | None = None,
) -> ReflexReference:
    return ReflexStateDetector(
        thresholds=thresholds
        or ReflexThresholds(low_hp_threshold=0.4)
    ).detect(
        hp_reference=_hp(hp_ratio),
        mp_reference=_mp(mp_ratio),
        death_signal=death,
        status_effects=status,
        ui_warnings=ui,
    )


def test_models_creation():
    assert ReflexStateType.LOW_HP.value == "LOW_HP"
    assert DangerEventType.HP_LOW.value == "HP_LOW"
    reference = ReflexReference(
        reflex_id="reflex-1",
        state=ReflexStateType.NORMAL,
        confidence=0.9,
    )
    assert reference.reflex_id == "reflex-1"
    assert reference.state is ReflexStateType.NORMAL
    assert reference.danger_events == []
    assert reference.ui_alerts == []


def test_hp_mp_reference():
    hp = HpMpReference(
        current_value=350,
        max_value=1000,
        ratio=0.35,
        confidence=0.9,
        source="mock",
    )
    assert hp.ratio == 0.35
    assert hp.current_value == 350
    assert hp.max_value == 1000
    assert hp.source == "mock"


def test_thresholds_data_driven():
    thresholds = ReflexThresholds.from_dict(
        {"low_hp_threshold": 0.4, "low_mp_threshold": 0.3}
    )
    assert thresholds.low_hp_threshold == 0.4
    assert thresholds.low_mp_threshold == 0.3
    assert thresholds.event_severity["DEATH"] == 1.0
    assert ReflexThresholds.from_dict(None).low_hp_threshold == 0.3


def test_detector_normal():
    reference = _detect(hp_ratio=0.8, mp_ratio=0.9)
    assert reference.state is ReflexStateType.NORMAL
    assert reference.danger_events == []
    assert reference.confidence == 0.9


def test_detector_low_hp():
    reference = _detect(hp_ratio=0.35, mp_ratio=0.8)
    assert reference.state is ReflexStateType.LOW_HP
    assert [e.event_type for e in reference.danger_events] == [
        DangerEventType.HP_LOW
    ]
    assert reference.confidence == 0.9


def test_detector_low_mp():
    reference = _detect(hp_ratio=0.8, mp_ratio=0.1)
    assert reference.state is ReflexStateType.LOW_MP
    assert [e.event_type for e in reference.danger_events] == [
        DangerEventType.MP_LOW
    ]


def test_detector_death():
    reference = _detect(hp_ratio=0.0, mp_ratio=0.5, death=True)
    assert reference.state is ReflexStateType.DEATH
    assert [e.event_type for e in reference.danger_events] == [
        DangerEventType.DEATH
    ]
    assert 0 <= reference.confidence <= 1


def test_detector_context_hp_fallback():
    context = MapleCompanionContextReference(
        player_context=MaplePlayerContext(
            player_id="p1",
            current_hp_reference=300,
            current_mp_reference=900,
            confidence=0.8,
        ),
        confidence=0.8,
        trace_id="trace-reflex",
    )
    reference = ReflexStateDetector(
        thresholds=ReflexThresholds(low_hp_threshold=0.4)
    ).detect(context_reference=context)
    assert reference.hp_reference is not None
    assert reference.hp_reference.ratio == 0.3
    assert reference.state is ReflexStateType.LOW_HP


def test_event_hp_low():
    events = DangerEventDetector().detect(hp_reference=_hp(0.2))
    assert len(events) == 1
    assert events[0].event_type is DangerEventType.HP_LOW
    assert events[0].severity == 0.6


def test_event_mp_low():
    events = DangerEventDetector().detect(mp_reference=_mp(0.1))
    assert len(events) == 1
    assert events[0].event_type is DangerEventType.MP_LOW


def test_event_death():
    events = DangerEventDetector().detect(
        hp_reference=_hp(0.5),
        death_signal=True,
    )
    assert len(events) == 1
    assert events[0].event_type is DangerEventType.DEATH
    assert events[0].severity == 1.0


def test_event_status_abnormal():
    events = DangerEventDetector().detect(
        hp_reference=_hp(0.8),
        mp_reference=_mp(0.8),
        status_effects=["中毒"],
    )
    assert any(
        event.event_type is DangerEventType.STATUS_ABNORMAL
        for event in events
    )


def test_event_ui_alert():
    events = DangerEventDetector().detect(
        hp_reference=_hp(0.8),
        mp_reference=_mp(0.8),
        ui_warnings=["背包已满"],
    )
    assert any(
        event.event_type is DangerEventType.UI_ALERT for event in events
    )


def test_validator_valid():
    reference = _detect(hp_ratio=0.35, mp_ratio=0.8)
    result = ReflexValidator().validate(reference)
    assert result.verdict is ReflexVerdict.VALID
    assert result.issues == []


def test_validator_warning():
    reference = _detect(hp_ratio=0.8)
    result = ReflexValidator().validate(reference)
    assert result.verdict is ReflexVerdict.WARNING
    assert any("missing" in issue for issue in result.issues)


def test_validator_blocked():
    reference = ReflexReference(reflex_id="")
    result = ReflexValidator().validate(reference)
    assert result.verdict is ReflexVerdict.BLOCKED
    assert "missing reflex id" in result.issues


def test_validator_blocked_invalid_state():
    reference = ReflexReference.model_construct(
        reflex_id="reflex-bad",
        state="BAD_STATE",
        confidence=0.9,
    )
    result = ReflexValidator().validate(reference)
    assert result.verdict is ReflexVerdict.BLOCKED
    assert "invalid state" in result.issues


def test_agent_loop_integration():
    reference = _detect(hp_ratio=0.35, mp_ratio=0.8)
    context = AgentLoopContext(
        trace_id="trace-reflex",
        status=AgentLoopStatus.OBSERVING,
        reflex_reference=reference,
    )
    assert context.reflex_reference is not None
    assert context.reflex_reference.state is ReflexStateType.LOW_HP


def test_replay_generation(tmp_path):
    reference = _detect(hp_ratio=0.35, mp_ratio=0.8)
    validation = ReflexValidator().validate(reference)
    thresholds = ReflexThresholds().to_dict()
    save_reflex_trace(
        tmp_path,
        "trace-replay",
        state=reference,
        hp_reference=reference.hp_reference,
        mp_reference=reference.mp_reference,
        danger_events=reference.danger_events,
        thresholds=thresholds,
        validation=validation.verdict.value,
    )
    replay = json.loads(
        (tmp_path / "trace-replay" / "reflex_trace.json").read_text(
            encoding="utf-8"
        )
    )
    assert replay["schema_version"] == "1.0"
    assert replay["state"]["state"] == "LOW_HP"
    assert replay["hp_reference"]["ratio"] == 0.35
    assert replay["mp_reference"]["ratio"] == 0.8
    assert replay["danger_events"][0]["event_type"] == "HP_LOW"
    assert replay["thresholds"]["low_hp_threshold"] == 0.3
    assert replay["validation"] == "VALID"


def test_webui_reflex_endpoint():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    reference = _detect(hp_ratio=0.35, mp_ratio=0.8)
    validation = ReflexValidator().validate(reference)
    payload = {
        "state": reference.state.value,
        "hp": (
            reference.hp_reference.model_dump(mode="json")
            if reference.hp_reference is not None
            else {}
        ),
        "mp": (
            reference.mp_reference.model_dump(mode="json")
            if reference.mp_reference is not None
            else {}
        ),
        "danger_events": [
            event.model_dump(mode="json")
            for event in reference.danger_events
        ],
        "ui_alerts": reference.ui_alerts,
        "confidence": reference.confidence,
        "reasoning": reference.reasoning,
        "validation": validation.verdict.value,
    }
    app = create_app(runtime=runtime, bus=bus, reflex=payload)
    with TestClient(app) as client:
        resp = client.get("/api/reflex/state")
    data = resp.json()
    assert resp.status_code == 200
    assert data["enabled"] is True
    assert data["state"] == "LOW_HP"
    assert data["hp"]["ratio"] == 0.35
    assert data["danger_events"][0]["event_type"] == "HP_LOW"
    assert data["confidence"] == 0.9
    assert data["validation"] == "VALID"


def test_webui_reflex_disabled():
    bus = EventBus()
    runtime = RuntimeManager(bus=bus)
    app = create_app(runtime=runtime, bus=bus)
    with TestClient(app) as client:
        resp = client.get("/api/reflex/state")
    assert resp.json()["enabled"] is False
