"""WindowBindingService:WindowInfo → BoundWindow(只读绑定)。"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import BaseModel, Field

from maple_agent.logging_setup import TraceContext
from maple_agent.window.models import WindowInfo

logger = logging.getLogger("maple_agent.window")


class BoundWindow(BaseModel):
    """已绑定窗口(只读,不控制)。"""

    window: WindowInfo
    client_offset: tuple[int, int]
    screen_offset: tuple[int, int]
    dpi_scale: float = Field(gt=0)
    coordinate_space: str = "client_logical"


class WindowBindingService:
    """把识别到的窗口登记为 BoundWindow,并落盘 window_context.json。"""

    def __init__(self, *, sessions_dir: str | Path = "sessions") -> None:
        self.sessions_dir = Path(sessions_dir)

    def bind(
        self,
        info: WindowInfo,
        *,
        trace_id: str | None = None,
    ) -> BoundWindow:
        with TraceContext(trace_id=trace_id):
            client_offset = (
                info.client_rect.left,
                info.client_rect.top,
            )
            screen_offset = (
                info.screen_rect.left,
                info.screen_rect.top,
            )
            bound = BoundWindow(
                window=info,
                client_offset=client_offset,
                screen_offset=screen_offset,
                dpi_scale=info.dpi_scale,
            )
            logger.info(
                "window bound: title=%s dpi=%s",
                info.title,
                info.dpi_scale,
            )
            self._write_replay(bound, trace_id)
            return bound

    def _write_replay(self, bound: BoundWindow, trace_id: str | None) -> None:
        resolved = trace_id or bound.window.trace_id
        if not resolved:
            return
        directory = self.sessions_dir / resolved
        directory.mkdir(parents=True, exist_ok=True)
        payload = {
            "trace_id": resolved,
            "window": bound.window.model_dump(mode="json"),
            "dpi_scale": bound.dpi_scale,
            "client_offset": list(bound.client_offset),
            "screen_offset": list(bound.screen_offset),
            "coordinate_space": bound.coordinate_space,
        }
        (directory / "window_context.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
