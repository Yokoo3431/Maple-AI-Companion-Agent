"""Event Bus 单测:强类型 / 枚举 / 优先级排序 / 订阅分发 / trace 集成。"""

import logging

import pytest
from pydantic import BaseModel, ValidationError

from maple_agent.events import Event, EventBus, EventType, Priority
from maple_agent.logging_setup import TraceContext, setup_logging


class HpPayload(BaseModel):
    hp: int
    max_hp: int


def test_event_type_enum_members():
    required = {
        EventType.START,
        EventType.READY,
        EventType.PAUSE,
        EventType.STOP,
        EventType.SCREEN_UPDATED,
        EventType.HP_LOW,
        EventType.GAME_WINDOW_LOST,
        EventType.PLAN_CREATED,
        EventType.PLAN_FAILED,
        EventType.ERROR_OCCURRED,
    }
    assert required <= set(EventType)


def test_event_model_fields():
    event = Event.create(EventType.START, source="tests")
    assert event.event_id
    assert event.event_type is EventType.START
    assert event.priority is Priority.NORMAL
    assert event.source == "tests"
    assert event.trace_id == ""
    assert event.payload is None


def test_event_rejects_bare_dict_payload():
    with pytest.raises(ValidationError):
        Event.create(EventType.HP_LOW, source="tests", payload={"hp": 1})


def test_event_accepts_typed_payload():
    event = Event.create(
        EventType.HP_LOW,
        source="vision",
        payload=HpPayload(hp=10, max_hp=100),
    )
    assert event.payload.hp == 10


def test_priority_defaults_per_type():
    assert Event.create(EventType.ERROR_OCCURRED, source="t").priority is Priority.CRITICAL
    assert Event.create(EventType.GAME_WINDOW_LOST, source="t").priority is Priority.HIGH
    assert Event.create(EventType.HP_LOW, source="t").priority is Priority.HIGH
    assert Event.create(EventType.PLAN_FAILED, source="t").priority is Priority.HIGH
    assert Event.create(EventType.SCREEN_UPDATED, source="t").priority is Priority.LOW
    assert Event.create(EventType.PLAN_CREATED, source="t").priority is Priority.NORMAL


def test_priority_override():
    event = Event.create(EventType.SCREEN_UPDATED, source="t", priority=Priority.CRITICAL)
    assert event.priority is Priority.CRITICAL


def test_trace_id_captured_from_context():
    with TraceContext.new() as tc:
        event = Event.create(EventType.PLAN_CREATED, source="agent")
    assert event.trace_id == tc.trace_id


@pytest.mark.asyncio
async def test_priority_ordering():
    bus = EventBus()
    received: list[Priority] = []
    bus.subscribe(lambda e: received.append(e.priority))
    await bus.start()
    bus.publish(Event.create(EventType.START, source="t", priority=Priority.NORMAL))
    bus.publish(Event.create(EventType.ERROR_OCCURRED, source="t", priority=Priority.CRITICAL))
    bus.publish(Event.create(EventType.HP_LOW, source="t", priority=Priority.LOW))
    bus.publish(Event.create(EventType.PLAN_CREATED, source="t", priority=Priority.HIGH))
    await bus.wait_idle()
    assert received == [
        Priority.CRITICAL,
        Priority.HIGH,
        Priority.NORMAL,
        Priority.LOW,
    ]
    await bus.stop()


@pytest.mark.asyncio
async def test_fifo_within_same_priority():
    bus = EventBus()
    received: list[str] = []
    bus.subscribe(lambda e: received.append(e.event_id))
    await bus.start()
    first = Event.create(EventType.START, source="t", priority=Priority.NORMAL)
    second = Event.create(EventType.READY, source="t", priority=Priority.NORMAL)
    bus.publish(first)
    bus.publish(second)
    await bus.wait_idle()
    assert received == [first.event_id, second.event_id]
    await bus.stop()


@pytest.mark.asyncio
async def test_subscribe_by_type_and_all():
    bus = EventBus()
    typed: list[EventType] = []
    all_events: list[EventType] = []
    bus.subscribe(lambda e: typed.append(e.event_type), event_type=EventType.HP_LOW)
    bus.subscribe(lambda e: all_events.append(e.event_type))
    await bus.start()
    bus.publish(Event.create(EventType.START, source="t", priority=Priority.NORMAL))
    bus.publish(Event.create(EventType.HP_LOW, source="t", priority=Priority.NORMAL))
    await bus.wait_idle()
    assert typed == [EventType.HP_LOW]
    assert all_events == [EventType.START, EventType.HP_LOW]
    await bus.stop()


@pytest.mark.asyncio
async def test_subscriber_error_isolated():
    bus = EventBus()
    received: list[EventType] = []

    def bad(_event: Event) -> None:
        raise RuntimeError("boom")

    bus.subscribe(bad)
    bus.subscribe(lambda e: received.append(e.event_type))
    await bus.start()
    bus.publish(Event.create(EventType.START, source="t"))
    await bus.wait_idle()
    assert received == [EventType.START]
    await bus.stop()


@pytest.mark.asyncio
async def test_trace_restored_for_subscribers(tmp_path):
    setup_logging(tmp_path, level="INFO", console=False)
    bus = EventBus()

    def handler(event: Event) -> None:
        logging.getLogger("maple_agent.agent.controller").info(
            "handled event=%s", event.event_type.value
        )

    bus.subscribe(handler)
    await bus.start()
    event = Event.create(EventType.PLAN_CREATED, source="agent", trace_id="fixed-trace-123")
    bus.publish(event)
    await bus.wait_idle()
    await bus.stop()

    agent_log = (tmp_path / "agent.log").read_text(encoding="utf-8")
    assert "handled event=agent.plan_created" in agent_log
    assert "trace=fixed-trace-123" in agent_log

    startup_log = (tmp_path / "startup.log").read_text(encoding="utf-8")
    assert "event published" in startup_log
    assert "trace=fixed-trace-123" in startup_log
