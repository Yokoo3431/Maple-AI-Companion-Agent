"""LLM Provider 契约与 Mock(Phase 0 不发起真实 API)。"""

from __future__ import annotations

from abc import abstractmethod
from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from maple_agent.events import EventBus, EventType
from maple_agent.providers.base import BaseProvider, ProviderError


class LLMRequest(BaseModel):
    """LLM 请求。"""

    prompt: str
    system: str = ""
    max_tokens: int = 512


class LLMResult(BaseModel):
    """LLM 响应。"""

    text: str
    model: str
    trace_id: str = ""
    finish_reason: str = "stop"


@runtime_checkable
class LLMProviderProtocol(Protocol):
    """LLM Provider 调用契约(结构化类型检查)。"""

    def complete(
        self, request: LLMRequest, *, trace_id: str | None = None
    ) -> LLMResult: ...


class LLMProvider(BaseProvider):
    """LLM 规划 Provider 抽象(未来可接 DeepSeek / OpenAI 兼容接口)。"""

    def __init__(self, *, bus: EventBus | None = None, model: str = "llm") -> None:
        super().__init__(
            name="llm",
            logger_name="maple_agent.agent.planner.llm",
            bus=bus,
        )
        self.model = model

    def complete(
        self, request: LLMRequest, *, trace_id: str | None = None
    ) -> LLMResult:
        return self._run_call(
            trace_id,
            success_event=EventType.PLAN_CREATED,
            failure_event=EventType.PLAN_FAILED,
            fn=lambda tid: self._complete(request, tid),
        )

    @abstractmethod
    def _complete(self, request: LLMRequest, tid: str) -> LLMResult: ...


class MockLLMProvider(LLMProvider):
    """Mock 实现:固定回复;可配置失败。"""

    def __init__(
        self,
        *,
        bus: EventBus | None = None,
        reply: str = "mock plan",
        raise_on_call: bool = False,
    ) -> None:
        super().__init__(bus=bus, model="mock-llm")
        self._reply = reply
        self._raise_on_call = raise_on_call
        self.call_count = 0

    def _complete(self, request: LLMRequest, tid: str) -> LLMResult:
        self.call_count += 1
        if self._raise_on_call:
            raise ProviderError("mock llm failure")
        return LLMResult(text=self._reply, model=self.model, trace_id=tid)
