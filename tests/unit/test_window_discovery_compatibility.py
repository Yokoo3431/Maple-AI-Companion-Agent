"""Phase 13-U.1a deterministic read-only window discovery tests."""

import sys
from types import SimpleNamespace

from maple_agent.window import (
    WindowCandidate,
    WindowsWindowDiscovery,
    default_game_window_profile,
    discover_window,
)

PROFILE = default_game_window_profile()


def test_maplestory_classic_cn_pair_matches():
    result = discover_window(
        [
            WindowCandidate(
                hwnd=101,
                pid=1001,
                process_name="Maplestory_Classic",
                window_title="冒险岛怀旧服",
            )
        ],
        PROFILE,
    )

    assert result.matched is True
    assert result.hwnd_available is True
    assert result.match_method == "process_and_title"
    assert result.confidence == 1.0


def test_legacy_maplestory_pair_matches():
    result = discover_window(
        [
            WindowCandidate(
                hwnd=102,
                pid=1002,
                process_name="MapleStory.exe",
                window_title="MapleStory",
            )
        ],
        PROFILE,
    )

    assert result.matched is True
    assert result.match_method == "process_and_title"


def test_unknown_process_and_title_do_not_match():
    result = discover_window(
        [
            WindowCandidate(
                hwnd=103,
                pid=1003,
                process_name="UnknownGame.exe",
                window_title="Unknown Game",
            )
        ],
        PROFILE,
    )

    assert result.matched is False
    assert result.reason == "no_profile_candidate_match"


def test_duplicate_candidates_choose_deterministically():
    result = discover_window(
        [
            WindowCandidate(
                hwnd=202,
                pid=2002,
                process_name="Maplestory_Classic.exe",
                window_title="冒险岛怀旧服",
            ),
            WindowCandidate(
                hwnd=201,
                pid=2001,
                process_name="Maplestory_Classic.exe",
                window_title="冒险岛怀旧服",
            ),
        ],
        PROFILE,
    )

    assert result.matched is True
    assert result.hwnd == 201
    assert result.pid == 2001


def test_no_visible_window_is_safe_failure():
    result = discover_window(
        [
            WindowCandidate(
                hwnd=104,
                pid=1004,
                process_name="Maplestory_Classic",
                window_title="冒险岛怀旧服",
                visible=False,
            )
        ],
        PROFILE,
    )

    assert result.matched is False
    assert result.hwnd_available is False
    assert result.reason == "no_visible_top_level_window"


def test_candidate_title_with_other_process_is_not_false_positive():
    result = discover_window(
        [
            WindowCandidate(
                hwnd=105,
                pid=1005,
                process_name="NotMaple.exe",
                window_title="冒险岛怀旧服",
            )
        ],
        PROFILE,
    )

    assert result.matched is False


def test_windows_discovery_uses_win32process_pid_api(monkeypatch):
    """真实 pywin32 将 GetWindowThreadProcessId 暴露在 win32process。"""
    fake_gui = SimpleNamespace(
        EnumWindows=lambda callback, unused: callback(106, unused),
        IsWindowVisible=lambda hwnd: True,
        GetWindowText=lambda hwnd: "冒险岛怀旧服",
    )
    fake_process = SimpleNamespace(
        GetWindowThreadProcessId=lambda hwnd: (0, 1006),
    )
    monkeypatch.setitem(sys.modules, "win32process", fake_process)

    result = WindowsWindowDiscovery(
        win32gui=fake_gui,
        process_name_resolver=lambda pid: "Maplestory_Classic",
    ).discover(PROFILE)

    assert result.matched is True
    assert result.match_method == "process_and_title"


def test_windows_discovery_skips_one_bad_window_metadata():
    callbacks = []

    def enum_windows(callback, unused):
        for hwnd in (107, 108):
            callbacks.append(hwnd)
            callback(hwnd, unused)

    fake_gui = SimpleNamespace(
        EnumWindows=enum_windows,
        IsWindowVisible=lambda hwnd: True,
        GetWindowThreadProcessId=lambda hwnd: (0, hwnd + 900),
        GetWindowText=lambda hwnd: (
            (_ for _ in ()).throw(RuntimeError("metadata unavailable"))
            if hwnd == 107
            else "MapleStory"
        ),
    )
    result = WindowsWindowDiscovery(
        win32gui=fake_gui,
        process_name_resolver=lambda pid: "Maplestory_Classic",
    ).discover(PROFILE)

    assert result.matched is True
    assert callbacks == [107, 108]
