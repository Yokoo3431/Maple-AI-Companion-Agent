"""VisionWorker 状态机与采集循环单测。"""

import asyncio

import pytest

from maple_agent.events import Event, EventBus, EventType
from maple_agent.providers.base import ProviderError
from maple_agent.vision import MockCaptureProvider, VisionWorker, VisionWorkerState


@pytest.mark.asyncio
async def test_worker_start_stop_states():
    bus = EventBus()
    capture = MockCaptureProvider()
    capture.initialize()
    worker = VisionWorker(capture, bus, interval=60)
    assert worker.state is VisionWorkerState.STOPPED
    worker.start()
    assert worker.state is VisionWorkerState.IDLE
    await worker.stop()
    assert worker.state is VisionWorkerState.STOPPED


@pytest.mark.asyncio
async def test_worker_tick_publishes_events_with_trace():
    bus = EventBus()
    events: list[Event] = []
    bus.subscribe(events.append)
    await bus.start()
    capture = MockCaptureProvider(bus=bus)
    capture.initialize()
    worker = VisionWorker(capture, bus, interval=60)
    worker.start()
    frame = await worker.tick()
    await bus.wait_idle()
    assert frame is not None
    assert worker.state is VisionWorkerState.IDLE
    assert worker.capture_count == 1
    assert worker.latest_frame is frame
    event_types = [e.event_type for e in events]
    assert EventType.SCREEN_CAPTURED in event_types
    assert EventType.SCREEN_UPDATED in event_types
    traces = {e.trace_id for e in events}
    assert traces == {frame.trace_id}
    await worker.stop()
    await bus.stop()


@pytest.mark.asyncio
async def test_worker_tick_error_state():
    bus = EventBus()
    capture = MockCaptureProvider(raise_on_capture=True)
    capture.initialize()
    worker = VisionWorker(capture, bus, interval=60)
    worker.start()
    with pytest.raises(ProviderError):
        await worker.tick()
    assert worker.state is VisionWorkerState.ERROR
    await worker.stop()
    assert worker.state is VisionWorkerState.STOPPED


@pytest.mark.asyncio
async def test_worker_loop_captures_repeatedly():
    bus = EventBus()
    capture = MockCaptureProvider()
    capture.initialize()
    worker = VisionWorker(capture, bus, interval=0.02)
    worker.start()
    await asyncio.sleep(0.15)
    assert worker.capture_count >= 2
    await worker.stop()
    assert worker.state is VisionWorkerState.STOPPED
