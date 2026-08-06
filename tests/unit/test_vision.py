"""Vision 模型 / 截图策略 / CaptureProvider 单测。"""

import pytest
from pydantic import ValidationError

from maple_agent.events import Event, EventBus, EventType
from maple_agent.game import MockGameWindowDetector, WindowInfo, WindowRect
from maple_agent.providers.base import ErrorPayload, ProviderError
from maple_agent.vision import (
    MockCaptureProvider,
    Observation,
    ScreenFrame,
    ScreenshotPolicy,
    VisionState,
    WindowsCaptureProvider,
)


def test_screen_frame_model_validation():
    frame = ScreenFrame(
        frame_id="f-1",
        captured_at="2026-08-06T00:00:00Z",
        width=1280,
        height=720,
    )
    assert frame.width == 1280
    assert frame.dpi_scale == 1.0
    with pytest.raises(ValidationError):
        ScreenFrame(frame_id="f-2", captured_at="2026-08-06T00:00:00Z", width=0, height=0)


def test_observation_model_and_bare_dict_rejected():
    obs = Observation(
        element="hp_bar",
        type="number",
        raw_value="850",
        normalized_value=850,
        confidence=0.97,
        source="mock",
    )
    assert obs.normalized_value == 850
    with pytest.raises(ValidationError):
        Observation(
            element="hp_bar",
            normalized_value={"hp": 850},  # 禁止裸 dict
        )


def test_vision_state_model():
    state = VisionState(frame_id="f-1", trace_id="t-1", hp=850, map_name="射手村")
    assert state.summary == ""
    assert state.observation_refs == []


def test_mock_capture_lifecycle_and_frame():
    capture = MockCaptureProvider(width=800, height=600)
    assert capture.status.value == "CREATED"
    with pytest.raises(ProviderError):
        capture.capture_frame()  # 未初始化
    capture.initialize()
    frame = capture.capture_frame(trace_id="t-1")
    assert isinstance(frame, ScreenFrame)
    assert frame.trace_id == "t-1"
    assert (frame.width, frame.height) == (800, 600)
    assert capture.call_count == 1
    capture.shutdown()
    assert capture.status.value == "SHUTDOWN"


@pytest.mark.asyncio
async def test_mock_capture_success_publishes_event():
    bus = EventBus()
    events: list[Event] = []
    bus.subscribe(events.append)
    await bus.start()
    capture = MockCaptureProvider(bus=bus)
    capture.initialize()
    capture.capture_frame(trace_id="t-captured")
    await bus.wait_idle()
    assert events[0].event_type is EventType.SCREEN_CAPTURED
    assert isinstance(events[0].payload, ScreenFrame)
    assert events[0].trace_id == "t-captured"
    await bus.stop()


@pytest.mark.asyncio
async def test_mock_capture_failure_publishes_error_event():
    bus = EventBus()
    events: list[Event] = []
    bus.subscribe(events.append)
    await bus.start()
    capture = MockCaptureProvider(bus=bus, raise_on_capture=True)
    capture.initialize()
    with pytest.raises(ProviderError):
        capture.capture_frame(trace_id="t-fail")
    await bus.wait_idle()
    assert events[0].event_type is EventType.ERROR_OCCURRED
    assert isinstance(events[0].payload, ErrorPayload)
    assert events[0].trace_id == "t-fail"
    await bus.stop()


def test_policy_save_and_capacity(tmp_path):
    policy = ScreenshotPolicy(save_enabled=True, max_images=2)
    capture = MockCaptureProvider(
        policy=policy,
        sessions_dir=tmp_path,
        width=64,
        height=48,
    )
    capture.initialize()
    for index in range(3):
        capture.capture_frame(trace_id=f"trace-{index}")
    pngs = list(tmp_path.rglob("frame.png"))
    assert len(pngs) == 2  # FIFO 清理后最多 2 张
    assert all(p.exists() for p in pngs)


def test_windows_capture_provider_guards():
    assert isinstance(WindowsCaptureProvider.is_supported(), bool)
    provider = WindowsCaptureProvider(detector=MockGameWindowDetector(None))
    provider.initialize()
    with pytest.raises(ProviderError):
        provider.capture_frame()


def test_windows_capture_provider_rejects_invalid_handle():
    window = WindowInfo(
        handle=0,
        title="MapleStory",
        process_name="MapleStory.exe",
        rect=WindowRect(left=0, top=0, width=800, height=600),
    )
    provider = WindowsCaptureProvider(detector=MockGameWindowDetector(window))
    provider.initialize()
    with pytest.raises(ProviderError):
        provider.capture_frame()
