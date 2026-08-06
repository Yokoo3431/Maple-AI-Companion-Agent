"""Storage Provider 契约与 Mock(Phase 0 仅内存存储)。"""

from __future__ import annotations

from abc import abstractmethod
from typing import Protocol, runtime_checkable

from pydantic import BaseModel

from maple_agent.events import EventBus, EventType
from maple_agent.providers.base import BaseProvider, ProviderError


@runtime_checkable
class StorageProviderProtocol(Protocol):
    """Storage Provider 调用契约。"""

    def save(self, key: str, value: BaseModel, *, trace_id: str | None = None) -> None: ...

    def load(self, key: str, *, trace_id: str | None = None) -> BaseModel | None: ...


class StorageProvider(BaseProvider):
    """持久化 Provider 抽象(未来接 SQLite / 文件)。"""

    def __init__(self, *, bus: EventBus | None = None) -> None:
        super().__init__(
            name="storage",
            logger_name="maple_agent.storage",
            bus=bus,
        )

    def save(
        self, key: str, value: BaseModel, *, trace_id: str | None = None
    ) -> None:
        self._run_call(
            trace_id,
            success_event=EventType.STORAGE_SAVED,
            failure_event=EventType.ERROR_OCCURRED,
            fn=lambda tid: self._save(key, value, tid),
        )

    def load(self, key: str, *, trace_id: str | None = None) -> BaseModel | None:
        return self._run_call(
            trace_id,
            success_event=EventType.STORAGE_LOADED,
            failure_event=EventType.ERROR_OCCURRED,
            fn=lambda tid: self._load(key, tid),
        )

    @abstractmethod
    def _save(self, key: str, value: BaseModel, tid: str) -> None: ...

    @abstractmethod
    def _load(self, key: str, tid: str) -> BaseModel | None: ...


class MockStorageProvider(StorageProvider):
    """Mock 实现:进程内字典存储;可配置失败。"""

    def __init__(
        self,
        *,
        bus: EventBus | None = None,
        raise_on_call: bool = False,
    ) -> None:
        super().__init__(bus=bus)
        self._store: dict[str, BaseModel] = {}
        self._raise_on_call = raise_on_call
        self.call_count = 0

    def _save(self, key: str, value: BaseModel, tid: str) -> None:
        self.call_count += 1
        if self._raise_on_call:
            raise ProviderError("mock storage failure")
        self._store[key] = value

    def _load(self, key: str, tid: str) -> BaseModel | None:
        self.call_count += 1
        if self._raise_on_call:
            raise ProviderError("mock storage failure")
        return self._store.get(key)
