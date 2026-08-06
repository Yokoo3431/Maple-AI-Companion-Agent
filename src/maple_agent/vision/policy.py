"""ScreenshotPolicy:截图保存与容量控制,避免长期运行积累大量文件。"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field


class ScreenshotPolicy(BaseModel):
    """截图落盘策略。"""

    save_enabled: bool = False
    max_images: int = Field(default=50, ge=1)
    ttl_seconds: int = Field(default=3600, ge=0)
    compression: Literal["png", "jpeg"] = "png"


def enforce_capacity(directory: Path, max_images: int, ttl_seconds: int) -> None:
    """按 TTL 与 FIFO(修改时间)清理目录内截图(含子目录)。"""
    if not directory.exists():
        return
    files = [p for p in directory.rglob("*") if p.is_file()]
    now = time.time()
    if ttl_seconds > 0:
        for path in files:
            try:
                if now - path.stat().st_mtime > ttl_seconds:
                    path.unlink(missing_ok=True)
            except OSError:
                pass
    files = [p for p in directory.rglob("*") if p.is_file()]
    files.sort(key=lambda p: p.stat().st_mtime)
    for path in files[: max(0, len(files) - max_images)]:
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
