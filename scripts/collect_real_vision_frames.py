"""通用真实帧采集器(Phase 13-I.3,只读)。

跨机器通用(不是 office/home 专用脚本):machine 标签 + CaptureManager 条件感知
捕获 + ROI 裁剪 + LOCAL RAW manifest。真实截图只存 sessions/(已 gitignore)。
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

from maple_agent.hybrid_vision import parse_resolution  # noqa: E402
from maple_agent.hybrid_vision.models import CaptureCondition  # noqa: E402
from maple_agent.hybrid_vision.profile import (  # noqa: E402
    VisionProfileRegistry,
    VisionProfileTransformer,
)
from maple_agent.real_vision.capture_manager import CaptureManager  # noqa: E402

ROI_NAMES = ("map_label", "hp", "mp", "quest", "dialog")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="通用真实帧采集(只读;窗口状态由用户手动切换)"
    )
    parser.add_argument("--machine", default="HOME")
    parser.add_argument("--window-title", default="冒险岛怀旧服")
    parser.add_argument("--profile", default="home_pc_2560x1440")
    parser.add_argument(
        "--client-resolution", default="",
        help="GAME CLIENT 分辨率(默认取 profile.resolution)",
    )
    parser.add_argument("--frames", type=int, default=20)
    parser.add_argument("--interval", type=float, default=0.3)
    parser.add_argument(
        "--condition",
        choices=[item.value for item in CaptureCondition],
        default=CaptureCondition.FOREGROUND.value,
    )
    parser.add_argument(
        "--output", default="",
        help="输出目录(默认 sessions/13i3_<machine>_<condition>)",
    )
    args = parser.parse_args()
    output = Path(
        args.output
        or f"sessions/13i3_{args.machine.lower()}_{args.condition.lower()}"
    )
    frames_dir = output / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    registry = VisionProfileRegistry()
    profile = registry.get(args.profile)
    if profile is None:
        print(f"PROFILE NOT FOUND: {args.profile}")
        return 1
    client_width, client_height = parse_resolution(
        args.client_resolution or profile.resolution
    )
    if client_width <= 0 or client_height <= 0:
        print(f"INVALID CLIENT RESOLUTION: {args.client_resolution or profile.resolution}")
        return 1
    # 归一化 ROI(与分辨率无关);每帧按实际尺寸换算,兼容窗口模式切换
    base_profile = registry.get(args.profile)
    normalized_rois = base_profile.resolved_rois(
        registry.get(base_profile.base_profile)
        if base_profile.base_profile
        else None
    )
    if not normalized_rois and base_profile.legacy_pixel_rois:
        migrated = VisionProfileTransformer.migrate_legacy(
            base_profile,
            client_width=client_width,
            client_height=client_height,
        )
        normalized_rois = migrated.normalized_rois
    manager = CaptureManager(
        window_title=args.window_title,
        save_dir=str(frames_dir),
    )
    print(
        f"MACHINE={args.machine} PROFILE={args.profile} "
        f"CLIENT={client_width}x{client_height} CONDITION={args.condition}"
    )
    print(f"PREFERRED_PROVIDER: {manager.preferred}")
    latencies: list[float] = []
    provider_counts: dict[str, int] = {}
    samples: list[dict] = []
    ok_count = 0
    for index in range(max(1, args.frames)):
        start = time.perf_counter()
        frame, provider, reason = manager.capture(
            condition=args.condition
        )
        latency = round((time.perf_counter() - start) * 1000, 2)
        latencies.append(latency)
        provider_counts[provider] = provider_counts.get(provider, 0) + 1
        status = "OK" if frame.confidence > 0 else "FAILED"
        if status == "OK":
            ok_count += 1
        image_path = Path(frame.image_reference)
        sample = {
            "sample_id": frame.frame_id,
            "machine": args.machine,
            "condition": args.condition,
            "provider": provider,
            "reason": reason,
            "status": status,
            "image_reference": str(image_path),
            "latency_ms": latency,
            "captured_at": frame.timestamp.isoformat(),
        }
        if image_path.is_file() and normalized_rois:
            from PIL import Image

            image = Image.open(image_path)
            frame_width, frame_height = image.size
            for name, roi in normalized_rois.items():
                roi = VisionProfileTransformer.to_pixel(
                    roi,
                    client_width=frame_width,
                    client_height=frame_height,
                    dpi_scale=profile.dpi_scale,
                )
                roi_dir = output / "roi" / name
                roi_dir.mkdir(parents=True, exist_ok=True)
                box = (
                    int(roi["x"]),
                    int(roi["y"]),
                    int(roi["x"]) + int(roi["width"]),
                    int(roi["y"]) + int(roi["height"]),
                )
                crop = image.crop(box)
                crop_path = roi_dir / f"{frame.frame_id}.png"
                crop.save(crop_path)
                sample.setdefault("roi_crops", {})[name] = str(crop_path)
        samples.append(sample)
        time.sleep(max(0.0, args.interval))

    window_info = {
        "hwnd": manager.wgc.last_window_info.get("hwnd"),
        "window_title": manager.wgc.last_window_info.get("window_title", ""),
        "minimized": manager.wgc.last_window_info.get("minimized", False),
        "visible": manager.wgc.last_window_info.get("visible", False),
        "client_resolution": f"{client_width}x{client_height}",
        "display_resolution": profile.display_resolution or "",
        "dpi_scale": profile.dpi_scale,
        "window_mode": profile.window_mode,
    }
    manifest = {
        "schema_version": "1.0",
        "privacy": "LOCAL RAW - do not commit",
        "machine": args.machine,
        "condition": args.condition,
        "profile": args.profile,
        "client_resolution": f"{client_width}x{client_height}",
        "display_resolution": profile.display_resolution or "",
        "window_info": window_info,
        "provider_counts": provider_counts,
        "capture_success_rate": round(ok_count / max(1, len(samples)), 4),
        "latency_ms": {
            "mean": round(statistics.mean(latencies), 2)
            if latencies
            else None,
            "p50": round(statistics.median(latencies), 2)
            if latencies
            else None,
            "p95": round(
                sorted(latencies)[max(0, int(0.95 * len(latencies)) - 1)],
                2,
            )
            if latencies
            else None,
            "max": round(max(latencies), 2) if latencies else None,
        },
        "samples": samples,
        "collected_at": datetime.now(UTC).isoformat(),
    }
    (output / "manifest_raw.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"CAPTURE_SUCCESS: {manifest['capture_success_rate']}")
    print(f"PROVIDERS: {provider_counts}")
    print(f"LATENCY: {manifest['latency_ms']}")
    print(f"LOCAL RAW: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
