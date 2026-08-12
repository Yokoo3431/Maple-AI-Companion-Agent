"""只读窗口发现:列出当前顶层可见窗口(Phase 13-I,禁止控制窗口)。

用途:当不知道 Maple 客户端实际窗口标题时,让用户从列表中选择。
本脚本只读取窗口元数据,不执行任何窗口操作。
"""

from __future__ import annotations

import argparse
import json
import sys


def _list_windows() -> list[dict]:
    try:
        import win32gui  # type: ignore[import-not-found]
        import win32process  # type: ignore[import-not-found]
    except ImportError:
        print(
            "win32 (pywin32) not available; "
            "install with `.venv\\Scripts\\python -m pip install pywin32`",
            file=sys.stderr,
        )
        return []

    results: list[dict] = []

    def _callback(handle: int, _unused) -> None:
        if not win32gui.IsWindowVisible(handle):
            return
        title = win32gui.GetWindowText(handle).strip()
        if not title:
            return
        rect = win32gui.GetWindowRect(handle)
        _, pid = win32process.GetWindowThreadProcessId(handle)
        process_name = ""
        try:
            import win32api  # type: ignore[import-not-found]

            process = win32api.OpenProcess(0x1000, False, pid)
            process_name = win32process.GetModuleFileNameEx(process, 0)
        except Exception:
            pass
        results.append(
            {
                "hwnd": handle,
                "title": title,
                "pid": pid,
                "process_name": process_name,
                "window_rect": {
                    "left": rect[0],
                    "top": rect[1],
                    "width": rect[2] - rect[0],
                    "height": rect[3] - rect[1],
                },
            }
        )

    win32gui.EnumWindows(_callback, None)
    return sorted(results, key=lambda item: item["title"].lower())


def main() -> int:
    parser = argparse.ArgumentParser(
        description="只读列出当前顶层可见窗口(供选择游戏客户端)"
    )
    parser.add_argument("--filter", default="", help="按标题子串过滤")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    args = parser.parse_args()
    windows = _list_windows()
    if args.filter:
        windows = [
            item
            for item in windows
            if args.filter.lower() in item["title"].lower()
        ]
    if args.json:
        print(json.dumps(windows, ensure_ascii=False, indent=2))
        return 0
    if not windows:
        print("no visible top-level windows found")
        return 0
    for item in windows:
        rect = item["window_rect"]
        print(
            f"[{item['hwnd']}] {item['title']} | "
            f"{rect['width']}x{rect['height']} @ "
            f"({rect['left']},{rect['top']}) | pid={item['pid']} | "
            f"{item['process_name']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
