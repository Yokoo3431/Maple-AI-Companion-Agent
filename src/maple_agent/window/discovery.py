"""Deterministic, read-only Windows top-level window discovery."""

from __future__ import annotations

from collections.abc import Callable, Iterable
from pathlib import PureWindowsPath
from types import ModuleType

from pydantic import BaseModel, ConfigDict, Field

from maple_agent.window.profile import GameWindowProfile


class WindowCandidate(BaseModel):
    """可测试的可见顶层窗口元数据;不保存到仓库。"""

    model_config = ConfigDict(frozen=True)

    hwnd: int = Field(ge=0)
    pid: int = Field(default=0, ge=0)
    process_name: str = ""
    window_title: str = ""
    visible: bool = True


class WindowDiscoveryResult(BaseModel):
    """窗口匹配证据;真实 PID/HWND 只存在运行时结果中。"""

    matched: bool
    hwnd_available: bool
    hwnd: int | None = None
    pid: int | None = None
    process_name: str = ""
    window_title: str = ""
    match_method: str = "none"
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reason: str


def _normalize_process(value: str) -> str:
    """比较 basename,大小写和 .exe 后缀,不修改原始值。"""
    normalized = value.strip().replace("/", "\\")
    if "\\" in normalized:
        normalized = PureWindowsPath(normalized).name
    if normalized.lower().endswith(".exe"):
        normalized = normalized[:-4]
    return normalized.casefold()


def _normalize_title(value: str) -> str:
    return " ".join(value.strip().casefold().split())


def _no_match(reason: str) -> WindowDiscoveryResult:
    return WindowDiscoveryResult(
        matched=False,
        hwnd_available=False,
        match_method="none",
        confidence=0.0,
        reason=reason,
    )


def discover_window(
    candidates: Iterable[WindowCandidate],
    profile: GameWindowProfile,
) -> WindowDiscoveryResult:
    """从可见顶层窗口中确定性选择 profile 匹配项。"""
    visible = [candidate for candidate in candidates if candidate.visible]
    if not visible:
        return _no_match("no_visible_top_level_window")

    process_names = {
        _normalize_process(value) for value in profile.process_candidates
    }
    titles = {_normalize_title(value) for value in profile.title_candidates}
    ranked: list[tuple[int, int, int, WindowCandidate, str, float]] = []
    for candidate in visible:
        process_match = (
            bool(candidate.process_name)
            and _normalize_process(candidate.process_name) in process_names
        )
        title_match = (
            bool(candidate.window_title)
            and _normalize_title(candidate.window_title) in titles
        )
        if process_match and title_match:
            score, method, confidence = 300, "process_and_title", 1.0
        elif process_match:
            score, method, confidence = 200, "process", 0.9
        elif title_match and not candidate.process_name:
            # 只有系统无法提供进程名时才允许 title-only,避免同名窗口误绑定。
            score, method, confidence = 100, "title", 0.75
        else:
            continue

        # 分数优先;同分时 hwnd/pid 升序,保证重复候选确定性。
        ranked.append(
            (
                -score,
                candidate.hwnd if candidate.hwnd else 2**63 - 1,
                candidate.pid if candidate.pid else 2**63 - 1,
                candidate,
                method,
                confidence,
            )
        )

    if not ranked:
        return _no_match("no_profile_candidate_match")

    _, _, _, selected, method, confidence = sorted(ranked, key=lambda item: item[:3])[0]
    if not selected.hwnd:
        return WindowDiscoveryResult(
            matched=False,
            hwnd_available=False,
            pid=selected.pid or None,
            process_name=selected.process_name,
            window_title=selected.window_title,
            match_method=method,
            confidence=confidence,
            reason="profile_match_without_hwnd",
        )
    return WindowDiscoveryResult(
        matched=True,
        hwnd_available=True,
        hwnd=selected.hwnd,
        pid=selected.pid or None,
        process_name=selected.process_name,
        window_title=selected.window_title,
        match_method=method,
        confidence=confidence,
        reason="profile_match",
    )


class WindowsWindowDiscovery:
    """pywin32 EnumWindows adapter;仅枚举和读取窗口元数据。"""

    def __init__(
        self,
        *,
        win32gui: ModuleType | None = None,
        process_name_resolver: Callable[[int], str] | None = None,
    ) -> None:
        self._win32gui = win32gui
        self._process_name_resolver = process_name_resolver

    def discover(self, profile: GameWindowProfile) -> WindowDiscoveryResult:
        win32gui = self._win32gui
        if win32gui is None:
            try:
                import win32gui as win32gui_module  # type: ignore[import-not-found]

                win32gui = win32gui_module
            except ImportError:
                return _no_match("win32_unavailable")

        if not hasattr(win32gui, "EnumWindows"):
            return _no_match("window_enumeration_unavailable")

        candidates: list[WindowCandidate] = []

        def callback(hwnd: int, _unused: object) -> None:
            try:
                if not win32gui.IsWindowVisible(hwnd):
                    return
                get_window_process = getattr(
                    win32gui,
                    "GetWindowThreadProcessId",
                    None,
                )
                if get_window_process is None:
                    import win32process  # type: ignore[import-not-found]

                    get_window_process = win32process.GetWindowThreadProcessId
                _, pid = get_window_process(hwnd)
                title = win32gui.GetWindowText(hwnd).strip()
                process_name = self._resolve_process_name(pid)
                candidates.append(
                    WindowCandidate(
                        hwnd=int(hwnd),
                        pid=int(pid),
                        process_name=process_name,
                        window_title=title,
                        visible=True,
                    )
                )
            except Exception:
                # 一个窗口元数据读取失败不应阻断其余顶层窗口的发现。
                return

        try:
            win32gui.EnumWindows(callback, None)
        except Exception:
            return _no_match("window_enumeration_failed")
        return discover_window(candidates, profile)

    def _resolve_process_name(self, pid: int) -> str:
        if self._process_name_resolver is not None:
            try:
                return self._process_name_resolver(pid)
            except Exception:
                return ""
        try:
            import win32api  # type: ignore[import-not-found]
            import win32con  # type: ignore[import-not-found]
            import win32process  # type: ignore[import-not-found]

            process = win32api.OpenProcess(
                getattr(win32con, "PROCESS_QUERY_LIMITED_INFORMATION", 0x1000),
                False,
                pid,
            )
            try:
                return win32process.GetModuleFileNameEx(process, 0)
            finally:
                win32api.CloseHandle(process)
        except Exception:
            return ""
