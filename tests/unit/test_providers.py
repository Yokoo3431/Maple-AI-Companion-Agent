"""Provider 抽象层单测:生命周期 / 异常处理 / 接口契约 / Event 发布。"""

import pytest

from maple_agent.events import Event, EventBus, EventType
from maple_agent.logging_setup import setup_logging
from maple_agent.providers import (
    LLMProvider,
    LLMProviderProtocol,
    LLMRequest,
    MockLLMProvider,
    MockOCRProvider,
    MockStorageProvider,
    MockVisionProvider,
    OCRProvider,
    OCRProviderProtocol,
    OCRRequest,
    ProviderError,
    ProviderProtocol,
    StorageProvider,
    StorageProviderProtocol,
    VisionProvider,
    VisionProviderProtocol,
)
from maple_agent.providers.base import ErrorPayload


def test_interfaces_are_abstract():
    for cls in (LLMProvider, OCRProvider, VisionProvider, StorageProvider):
        with pytest.raises(TypeError):
            cls()


def test_mocks_satisfy_protocols():
    assert isinstance(MockLLMProvider(), LLMProviderProtocol)
    assert isinstance(MockOCRProvider(), OCRProviderProtocol)
    assert isinstance(MockVisionProvider(), VisionProviderProtocol)
    assert isinstance(MockStorageProvider(), StorageProviderProtocol)
    assert isinstance(MockLLMProvider(), ProviderProtocol)


def test_mock_lifecycle():
    provider = MockLLMProvider()
    assert provider.status.value == "CREATED"
    provider.initialize()
    assert provider.status.value == "INITIALIZED"
    provider.shutdown()
    assert provider.status.value == "SHUTDOWN"


def test_double_initialize_rejected():
    provider = MockLLMProvider()
    provider.initialize()
    with pytest.raises(ProviderError):
        provider.initialize()


def test_call_before_initialize_rejected():
    provider = MockLLMProvider()
    with pytest.raises(ProviderError):
        provider.complete(LLMRequest(prompt="hi"))


def test_call_after_shutdown_rejected():
    provider = MockLLMProvider()
    provider.initialize()
    provider.shutdown()
    with pytest.raises(ProviderError):
        provider.complete(LLMRequest(prompt="hi"))


def test_llm_mock_call_with_trace():
    provider = MockLLMProvider(reply="去射手村补给")
    provider.initialize()
    result = provider.complete(
        LLMRequest(prompt="下一步做什么?"),
        trace_id="trace-llm-1",
    )
    assert result.text == "去射手村补给"
    assert result.trace_id == "trace-llm-1"
    assert provider.call_count == 1


def test_trace_id_generated_when_missing():
    provider = MockLLMProvider()
    provider.initialize()
    result = provider.complete(LLMRequest(prompt="hi"))
    assert result.trace_id


def test_ocr_mock_call():
    provider = MockOCRProvider(text="勇士部落", confidence=0.88)
    provider.initialize()
    result = provider.recognize(OCRRequest(image_path=""), trace_id="trace-ocr-1")
    assert result.text == "勇士部落"
    assert result.confidence == 0.88
    assert result.trace_id == "trace-ocr-1"


def test_vision_mock_call():
    provider = MockVisionProvider()
    provider.initialize()
    result = provider.capture_state(trace_id="trace-vision-1")
    assert result.hp == 1000
    assert result.map_name == "射手村"
    assert result.trace_id == "trace-vision-1"


def test_storage_roundtrip():
    provider = MockStorageProvider()
    provider.initialize()
    value = LLMRequest(prompt="记住这个")
    provider.save("last-plan", value, trace_id="trace-storage-1")
    loaded = provider.load("last-plan", trace_id="trace-storage-2")
    assert loaded == value
    assert provider.load("missing", trace_id="trace-storage-3") is None


@pytest.mark.asyncio
async def test_failure_emits_error_event(tmp_path):
    setup_logging(tmp_path, level="INFO", console=False)
    bus = EventBus()
    events: list[Event] = []
    bus.subscribe(events.append)
    await bus.start()
    provider = MockLLMProvider(bus=bus, raise_on_call=True)
    provider.initialize()
    with pytest.raises(ProviderError):
        provider.complete(LLMRequest(prompt="hi"), trace_id="trace-fail-1")
    await bus.wait_idle()
    assert events and events[0].event_type is EventType.PLAN_FAILED
    assert isinstance(events[0].payload, ErrorPayload)
    assert events[0].payload.message == "mock llm failure"
    assert events[0].trace_id == "trace-fail-1"

    agent_log = (tmp_path / "agent.log").read_text(encoding="utf-8")
    assert "provider call failed" in agent_log
    assert "trace=trace-fail-1" in agent_log
    await bus.stop()


@pytest.mark.asyncio
async def test_success_emits_typed_event():
    bus = EventBus()
    events: list[Event] = []
    bus.subscribe(events.append)
    await bus.start()
    provider = MockVisionProvider(bus=bus)
    provider.initialize()
    provider.capture_state(trace_id="trace-ok-1")
    await bus.wait_idle()
    assert events[0].event_type is EventType.SCREEN_UPDATED
    assert events[0].payload.hp == 1000
    assert events[0].trace_id == "trace-ok-1"
    await bus.stop()


@pytest.mark.asyncio
async def test_storage_events():
    bus = EventBus()
    event_types: list[EventType] = []
    bus.subscribe(lambda e: event_types.append(e.event_type))
    await bus.start()
    provider = MockStorageProvider(bus=bus)
    provider.initialize()
    provider.save("k", LLMRequest(prompt="v"), trace_id="trace-s-1")
    provider.load("k", trace_id="trace-s-2")
    await bus.wait_idle()
    assert event_types == [EventType.STORAGE_SAVED, EventType.STORAGE_LOADED]
    await bus.stop()


@pytest.mark.asyncio
async def test_provider_logs_to_correct_files(tmp_path):
    setup_logging(tmp_path, level="INFO", console=False)
    bus = EventBus()
    await bus.start()
    llm = MockLLMProvider(bus=bus)
    llm.initialize()
    llm.complete(LLMRequest(prompt="x"), trace_id="trace-log-1")
    ocr = MockOCRProvider(bus=bus)
    ocr.initialize()
    ocr.recognize(OCRRequest(), trace_id="trace-log-2")
    await bus.wait_idle()
    agent_log = (tmp_path / "agent.log").read_text(encoding="utf-8")
    vision_log = (tmp_path / "vision.log").read_text(encoding="utf-8")
    assert "provider call start: llm" in agent_log
    assert "trace=trace-log-1" in agent_log
    assert "provider call start: ocr" in vision_log
    assert "trace=trace-log-2" in vision_log
    await bus.stop()
