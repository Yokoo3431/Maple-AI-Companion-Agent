"""Capture Condition 只读探针(Phase 13-I.1)。

四种条件分别测量:FOREGROUND / BACKGROUND_VISIBLE / BACKGROUND_OCCLUDED /
MINIMIZED。窗口状态由用户手动切换,Agent 禁止激活/最小化/恢复窗口。
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from maple_agent.hybrid_vision import (  # noqa: E402
    CaptureCondition,
    window_state_from_provider,
)
from maple_agent.real_vision import WindowsScreenshotProvider  # noqa: E402


def _image_stats(path: Path) -> dict:
    try:
        from PIL import Image, ImageStat

        image = Image.open(path).convert("L")
        stats = ImageStat.Stat(image)
        return {
            "mean": round(stats.mean[0], 2),
            "stddev": round(stats.stddev[0], 2),
            "black_frame": bool(stats.mean[0] < 5.0 or stats.stddev[0] < 6.0),
        }
    except Exception:
        return {"mean": None, "stddev": None, "black_frame": None}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture condition probe(只读;窗口状态由用户切换)"
    )
    parser.add_argument("--window-title", default="冒险岛怀旧服")
    parser.add_argument(
        "--condition",
        choices=[item.value for item in CaptureCondition],
        required=True,
    )
    parser.add_argument("--frames", type=int, default=3)
    parser.add_argument("--interval", type=float, default=0.3)
    parser.add_argument(
        "--output", default="sessions/capture_conditions"
    )
    args = parser.parse_args()
    condition = CaptureCondition(args.condition)
    output = Path(args.output) / condition.value.lower()
    output.mkdir(parents=True, exist_ok=True)
    provider = WindowsScreenshotProvider(
        window_title=args.window_title,
        save_dir=str(output),
    )
    window_state = provider.discover_window()
    measured = window_state_from_provider(provider)
    print(f"CONDITION_REQUESTED: {condition.value}")
    print(f"MEASURED_STATE: {json.dumps(measured, ensure_ascii=False)}")
    binding = window_state.get("binding", "NOT_FOUND")
    if binding != "BOUND":
        print(f"WINDOW NOT FOUND -> {condition.value} = NOT_TESTED")
        return 0
    latencies: list[float] = []
    frames: list[dict] = []
    ok_count = 0
    black_count = 0
    for index in range(max(1, args.frames)):
        start = time.perf_counter()
        frame = provider.capture()
        latency = round((time.perf_counter() - start) * 1000, 2)
        latencies.append(latency)
        status = provider.last_status.value
        path = Path(frame.image_reference)
        stats = _image_stats(path) if path.is_file() else {}
        if status == "OK":
            ok_count += 1
        if stats.get("black_frame"):
            black_count += 1
        frames.append(
            {
                "frame_id": frame.frame_id,
                "status": status,
                "method": provider.capture_method,
                "latency_ms": latency,
                "image": str(path),
                "image_stats": stats,
            }
        )
        time.sleep(max(0.0, args.interval))
    report = {
        "schema_version": "1.0",
        "privacy": "LOCAL RAW - do not commit",
        "condition": condition.value,
        "window_state_measured": measured,
        "capture": {
            "frames": len(frames),
            "success_rate": round(ok_count / max(1, len(frames)), 4),
            "black_frames": black_count,
            "method": provider.capture_method,
            "fallback_reason": provider.fallback_reason,
            "latency_ms": {
                "mean": round(statistics.mean(latencies), 2)
                if latencies
                else None,
                "p95": round(
                    sorted(latencies)[
                        max(0, int(0.95 * len(latencies)) - 1)
                    ],
                    2,
                )
                if latencies
                else None,
            },
            "frame_records": frames,
        },
        "captured_at": datetime.now(UTC).isoformat(),
    }
    (output / "condition_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"CAPTURE_SUCCESS: {report['capture']['success_rate']}")
    print(f"BLACK_FRAMES: {black_count}")
    print(f"METHOD: {provider.capture_method}")
    print(
        f"REPORT: {output / 'condition_report.json'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
