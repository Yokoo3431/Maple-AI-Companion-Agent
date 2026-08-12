"""Windows.Graphics.Capture(WGC)只读可行性探针(Phase 13-I.1)。

通过 `windows-capture`(WinRT WGC 封装)尝试窗口捕获;包未安装/API 失败时
诚实输出 WGC_UNAVAILABLE。不执行任何窗口控制。
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Windows.Graphics.Capture feasibility probe(只读)"
    )
    parser.add_argument("--window-title", default="冒险岛怀旧服")
    parser.add_argument("--frames", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--output", default="sessions/wgc_probe")
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    report: dict = {
        "schema_version": "1.0",
        "privacy": "LOCAL RAW - do not commit",
        "provider": "windows.graphics.capture",
        "requested_title": args.window_title,
        "captured_at": datetime.now(UTC).isoformat(),
    }
    try:
        import win32gui  # type: ignore[import-not-found]
    except ImportError:
        report["status"] = "WGC_UNAVAILABLE"
        report["reason"] = "pywin32 not available (window discovery)"
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    hwnd = win32gui.FindWindow(None, args.window_title)
    if not hwnd:
        report["status"] = "WGC_UNAVAILABLE"
        report["reason"] = "window not found"
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    report["hwnd"] = hwnd
    if importlib.util.find_spec("windows_capture") is None:
        report["status"] = "WGC_UNAVAILABLE"
        report["reason"] = "windows-capture package not installed"
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    latencies: list[float] = []
    frame_paths: list[str] = []
    errors: list[str] = []

    def on_frame(frame) -> None:
        start = time.perf_counter()
        path = output / f"wgc_{len(frame_paths):03d}.png"
        frame.save_as_image(str(path))
        latencies.append(round((time.perf_counter() - start) * 1000, 2))
        frame_paths.append(str(path))

    try:
        from windows_capture import WindowsCapture  # type: ignore

        capture = WindowsCapture(
            window_hwnd=hwnd,
            cursor_capture=False,
            draw_border=False,
        )

        @capture.event
        def on_frame_arrived(frame, control) -> None:
            on_frame(frame)
            if len(frame_paths) >= max(1, args.frames):
                control.stop()

        @capture.event
        def on_closed() -> None:
            pass

        control = capture.start_free_threaded()
        deadline = time.time() + max(1.0, args.timeout)
        while (
            time.time() < deadline
            and len(frame_paths) < max(1, args.frames)
            and not control.is_finished()
        ):
            time.sleep(0.2)
        control.stop()
        control.wait()
    except Exception as exc:
        errors.append(f"{type(exc).__name__}: {exc}")
        report["status"] = (
            "WGC_AVAILABLE_BUT_CAPTURE_FAILED"
            if frame_paths
            else "WGC_CAPTURE_FAILED"
        )
        report["errors"] = errors
        report["frames_received"] = len(frame_paths)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    report["status"] = "WGC_OK" if frame_paths else "WGC_EMPTY"
    report["frames_received"] = len(frame_paths)
    report["latency_ms"] = {
        "mean": round(sum(latencies) / len(latencies), 2)
        if latencies
        else None,
        "max": round(max(latencies), 2) if latencies else None,
    }
    report["frame_paths"] = frame_paths
    (output / "wgc_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
