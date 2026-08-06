"""日志系统基础设施(Phase 0,仅建基础设施,不含输入/OCR/游戏逻辑)。

- 分模块输出:startup / runtime / agent / vision / input / task;
- error.log 汇总 ERROR / CRITICAL;
- 所有记录自动携带 trace_id / correlation_id,一次 Agent 行为链可跨文件关联;
- 固定等级:DEBUG / INFO / WARNING / ERROR / CRITICAL;
- 日志文件按大小轮转。
"""

from __future__ import annotations

import contextvars
import logging
import logging.handlers
import uuid
from pathlib import Path
from typing import Literal

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]

_STANDARD_LEVELS: tuple[str, ...] = ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL")

_CATEGORY_FILES: dict[str, str] = {
    "startup": "startup.log",
    "runtime": "runtime.log",
    "agent": "agent.log",
    "vision": "vision.log",
    "input": "input.log",
    "task": "task.log",
}

_CATEGORY_PREFIXES: tuple[tuple[str, str], ...] = (
    ("maple_agent.runtime", "runtime"),
    ("maple_agent.agent", "agent"),
    ("maple_agent.vision", "vision"),
    ("maple_agent.input", "input"),
    ("maple_agent.task", "task"),
)

_trace_var: contextvars.ContextVar[str] = contextvars.ContextVar("maple_trace_id", default="")
_correlation_var: contextvars.ContextVar[str] = contextvars.ContextVar(
    "maple_correlation_id", default=""
)


def new_id() -> str:
    """生成紧凑唯一 ID(用于 trace_id / correlation_id)。"""
    return uuid.uuid4().hex[:12]


class TraceContext:
    """Agent 行为链追踪上下文。

    用法:
        with TraceContext.new() as trace:
            logger.info("step 1")  # 自动携带 trace_id / correlation_id
    """

    def __init__(
        self,
        trace_id: str | None = None,
        correlation_id: str | None = None,
    ) -> None:
        self.trace_id = trace_id or new_id()
        self.correlation_id = correlation_id or self.trace_id
        self._trace_token: contextvars.Token[str] | None = None
        self._correlation_token: contextvars.Token[str] | None = None

    @classmethod
    def new(cls, correlation_id: str | None = None) -> TraceContext:
        return cls(correlation_id=correlation_id)

    def __enter__(self) -> TraceContext:
        self._trace_token = _trace_var.set(self.trace_id)
        self._correlation_token = _correlation_var.set(self.correlation_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._trace_token is not None:
            _trace_var.reset(self._trace_token)
        if self._correlation_token is not None:
            _correlation_var.reset(self._correlation_token)

    @staticmethod
    def current() -> tuple[str, str]:
        """返回当前 (trace_id, correlation_id);未设置时均为空字符串。"""
        return _trace_var.get(), _correlation_var.get()


def category_for(logger_name: str) -> str:
    """根据 logger 名映射日志文件类别;未匹配的模块归入 startup。"""
    for prefix, category in _CATEGORY_PREFIXES:
        if logger_name == prefix or logger_name.startswith(f"{prefix}."):
            return category
    return "startup"


def level_number(level: LogLevel) -> int:
    """将固定等级名转为 logging 数值;非固定等级直接报错。"""
    if level not in _STANDARD_LEVELS:
        raise ValueError(f"不支持的日志等级: {level!r};固定等级: {_STANDARD_LEVELS}")
    return getattr(logging, level)


class TraceFilter(logging.Filter):
    """为每条记录注入 trace_id / correlation_id。"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.trace_id = _trace_var.get()
        record.correlation_id = _correlation_var.get()
        return True


class CategoryFilter(logging.Filter):
    """只放行属于指定类别的记录。"""

    def __init__(self, category: str) -> None:
        super().__init__()
        self.category = category

    def filter(self, record: logging.LogRecord) -> bool:
        return category_for(record.name) == self.category


class TraceFormatter(logging.Formatter):
    """文本格式:时间 [级别] [模块] trace=... corr=... 消息。"""

    def format(self, record: logging.LogRecord) -> str:
        record.asctime = self.formatTime(record, self.datefmt)
        trace_id = getattr(record, "trace_id", "") or ""
        correlation_id = getattr(record, "correlation_id", "") or ""
        line = (
            f"{record.asctime} [{record.levelname}] [{record.name}] "
            f"trace={trace_id} corr={correlation_id} {record.getMessage()}"
        )
        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


def _make_handler(
    path: Path,
    level: int,
    max_bytes: int,
    backup_count: int,
    filters: list[logging.Filter],
) -> logging.Handler:
    handler = logging.handlers.RotatingFileHandler(
        path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(TraceFormatter())
    for flt in filters:
        handler.addFilter(flt)
    return handler


def setup_logging(
    logs_dir: str | Path = "logs",
    level: LogLevel = "INFO",
    max_bytes: int = 1_000_000,
    backup_count: int = 5,
    console: bool = True,
) -> Path:
    """配置根日志器:分模块文件 + error.log + 可选控制台输出。"""
    level_num = level_number(level)
    logs_path = Path(logs_dir)
    logs_path.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(level_num)
    root.handlers.clear()

    trace_filter = TraceFilter()
    for category, filename in _CATEGORY_FILES.items():
        root.addHandler(
            _make_handler(
                logs_path / filename,
                level_num,
                max_bytes,
                backup_count,
                [trace_filter, CategoryFilter(category)],
            )
        )

    root.addHandler(
        _make_handler(
            logs_path / "error.log",
            logging.ERROR,
            max_bytes,
            backup_count,
            [trace_filter],
        )
    )

    if console:
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level_num)
        console_handler.setFormatter(TraceFormatter())
        console_handler.addFilter(trace_filter)
        root.addHandler(console_handler)

    logging.getLogger("maple_agent").info(
        "logging initialized: level=%s dir=%s max_bytes=%d backup_count=%d",
        level,
        logs_path,
        max_bytes,
        backup_count,
    )
    return logs_path
