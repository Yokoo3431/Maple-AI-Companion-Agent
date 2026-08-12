"""CaptureCondition 分类与只读窗口状态探针。"""

from __future__ import annotations

from maple_agent.hybrid_vision.models import CaptureCondition


def classify_window_state(
    *,
    foreground: bool = False,
    minimized: bool = False,
    visible: bool = False,
) -> CaptureCondition:
    """根据窗口状态分类捕获条件。

    BACKGROUND_VISIBLE vs BACKGROUND_OCCLUDED 无法仅凭窗口状态区分,
    需要截图内容证据;调用方应结合人工标注/内容分析给出细分。
    """
    if minimized:
        return CaptureCondition.MINIMIZED
    if foreground and visible:
        return CaptureCondition.FOREGROUND
    if visible:
        return CaptureCondition.BACKGROUND_VISIBLE
    return CaptureCondition.BACKGROUND_OCCLUDED


def window_state_from_provider(provider) -> dict:
    """复用 WindowsScreenshotProvider 的窗口元数据。"""
    info = getattr(provider, "last_window_info", {}) or {}
    condition = classify_window_state(
        foreground=bool(info.get("foreground", False)),
        minimized=bool(info.get("minimized", False)),
        visible=bool(info.get("visible", False)),
    )
    return {
        "condition": condition.value,
        "foreground": bool(info.get("foreground", False)),
        "minimized": bool(info.get("minimized", False)),
        "visible": bool(info.get("visible", False)),
        "hwnd": info.get("hwnd"),
        "resolution": info.get("resolution", ""),
    }
