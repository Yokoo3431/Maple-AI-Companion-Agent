"""Runtime 状态机单测:迁移表 / 非法跳转 / 事件发布 / 日志 / Bus 消费。"""

import pytest

from maple_agent.events import Event, EventBus, EventType
from maple_agent.game.window import MockGameWindowDetector, WindowInfo, WindowRect
from maple_agent.logging_setup import setup_logging
from maple_agent.runtime import (
    IllegalTransitionError,
    RuntimeGateError,
    RuntimeManager,
    RuntimeState,
    allowed_transitions,
)


def _manager(bus: EventBus) -> RuntimeManager:
    manager = RuntimeManager(bus=bus)
    manager.attach()
    return manager


def _window() -> WindowInfo:
    return WindowInfo(
        handle=12345,
        title="MapleStory",
        process_name="MapleStory.exe",
        rect=WindowRect(left=0, top=0, width=800, height=600),
    )


def test_initial_state_offline():
    manager = RuntimeManager(bus=EventBus())
    assert manager.state is RuntimeState.OFFLINE


def test_all_states_covered_by_transition_table():
    states = {state for pair in allowed_transitions() for state in pair}
    assert states == set(RuntimeState)


def test_illegal_transition_rejected():
    manager = RuntimeManager(bus=EventBus())
    with pytest.raises(IllegalTransitionError):
        manager.pause()  # OFFLINE -> PAUSED 非法
    assert manager.state is RuntimeState.OFFLINE

    manager.start()
    with pytest.raises(IllegalTransitionError):
        manager.pause()  # READY -> PAUSED 非法
    assert manager.state is RuntimeState.READY


@pytest.mark.asyncio
async def test_start_reaches_ready_and_publishes_events():
    bus = EventBus()
    received: list[Event] = []
    bus.subscribe(received.append)
    await bus.start()
    manager = _manager(bus)
    manager.start()
    await bus.wait_idle()
    assert manager.state is RuntimeState.READY
    assert [e.event_type for e in received] == [EventType.STARTING, EventType.READY]
    await bus.stop()


@pytest.mark.asyncio
async def test_full_lifecycle_event_sequence():
    bus = EventBus()
    received: list[EventType] = []
    bus.subscribe(lambda e: received.append(e.event_type))
    await bus.start()
    manager = _manager(bus)
    detector = MockGameWindowDetector(_window())
    manager.start()
    manager.confirm()
    manager.start_agent(detector=detector)
    manager.pause()
    manager.resume(detector=detector)
    manager.stop()
    await bus.wait_idle()
    assert manager.state is RuntimeState.OFFLINE
    assert received == [
        EventType.STARTING,
        EventType.READY,
        EventType.RUNNING,
        EventType.PAUSE,
        EventType.RUNNING,
        EventType.STOPPING,
        EventType.STOPPED,
    ]
    await bus.stop()


@pytest.mark.asyncio
async def test_state_change_logs_runtime_with_trace(tmp_path):
    setup_logging(tmp_path, level="INFO", console=False)
    bus = EventBus()
    received: list[str] = []
    bus.subscribe(lambda e: received.append(e.trace_id))
    await bus.start()
    manager = _manager(bus)
    manager.start(trace_id="trace-runtime-1")
    await bus.wait_idle()
    runtime_log = (tmp_path / "runtime.log").read_text(encoding="utf-8")
    assert "OFFLINE -> STARTING" in runtime_log
    assert "STARTING -> READY" in runtime_log
    assert "trace=trace-runtime-1" in runtime_log
    assert received == ["trace-runtime-1", "trace-runtime-1"]
    await bus.stop()


@pytest.mark.asyncio
async def test_consumes_bus_commands():
    bus = EventBus()
    await bus.start()
    manager = _manager(bus)
    detector = MockGameWindowDetector(_window())

    bus.publish(Event.create(EventType.START, source="webui"))
    await bus.wait_idle()
    assert manager.state is RuntimeState.READY

    manager.confirm()
    manager.start_agent(detector=detector)
    assert manager.state is RuntimeState.RUNNING

    bus.publish(Event.create(EventType.GAME_WINDOW_LOST, source="vision"))
    await bus.wait_idle()
    assert manager.state is RuntimeState.PAUSED

    manager.resume(detector=detector)
    bus.publish(Event.create(EventType.PAUSE, source="webui"))
    await bus.wait_idle()
    assert manager.state is RuntimeState.PAUSED

    bus.publish(Event.create(EventType.STOP, source="webui"))
    await bus.wait_idle()
    assert manager.state is RuntimeState.OFFLINE
    await bus.stop()


def test_self_events_ignored():
    bus = EventBus()
    manager = _manager(bus)
    detector = MockGameWindowDetector(_window())
    manager.start()
    manager.confirm()
    manager.start_agent(detector=detector)
    manager.pause()  # 发布 PAUSE;若无来源过滤会触发 PAUSED -> PAUSED 非法跳转
    assert manager.state is RuntimeState.PAUSED
    manager.stop()
    assert manager.state is RuntimeState.OFFLINE


def test_running_gate_requires_confirmation_and_window():
    bus = EventBus()
    manager = _manager(bus)
    manager.start()
    with pytest.raises(RuntimeGateError):
        manager.start_agent()  # 未确认
    manager.confirm()
    with pytest.raises(RuntimeGateError):
        manager.start_agent(detector=MockGameWindowDetector(None))  # 窗口不存在
    assert manager.state is RuntimeState.READY
    manager.start_agent(detector=MockGameWindowDetector(_window()))
    assert manager.state is RuntimeState.RUNNING
