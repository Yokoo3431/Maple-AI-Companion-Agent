"""事件驱动视觉调度 trace(Phase 13-I.3,只读)。

验证:CaptureManager -> FrameChangeDetector -> VisionScheduler ->
geometry/template/OCR selective path。
真实静态帧(idle)+ deterministic fixture(HP/MP change、map change)混合验证,
REAL 与 FIXTURE 明确分离标注。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from maple_agent.hybrid_vision import (  # noqa: E402
    BenchmarkPrivacySanitizer,
    FrameChangeDetector,
    HpMpGeometryExtractor,
    MapleVisualTemplateLibrary,
    VisionScheduler,
    parse_resolution,
    resolve_pixel_rois_for,
)
from maple_agent.hybrid_vision.models import PerceptionMethod  # noqa: E402
from maple_agent.hybrid_vision.profile import VisionProfileRegistry  # noqa: E402


def _collect_frames(frames_dir: Path) -> list[Path]:
    if not frames_dir.is_dir():
        return []
    return sorted(frames_dir.glob("*.png"))


def _fixture_modify_hpmp(source: Path, target: Path, *, ratio: float, kind: str):
    """fixture:在真实帧副本上绘制 HP/MP 条变化(仅本地)。"""
    from PIL import Image, ImageDraw

    image = Image.open(source).convert("RGB")
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 40, 40), fill=(255, 255, 255))
    draw.text((4, 4), f"{kind}{ratio}", fill=(255, 255, 255))
    image.save(target)


def _fixture_modify_map(source: Path, target: Path):
    """fixture:真实帧副本上标记 map 区域变化。"""
    from PIL import Image, ImageDraw

    image = Image.open(source).convert("RGB")
    draw = ImageDraw.Draw(image)
    draw.rectangle((10, 10, 120, 40), fill=(255, 255, 255))
    draw.text((16, 16), "MAPCHANGED", fill=(0, 0, 0))
    image.save(target)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="事件驱动视觉调度 trace(只读)"
    )
    parser.add_argument("--frames-dir", default="")
    parser.add_argument("--profile", default="home_pc_2560x1440")
    parser.add_argument("--client-resolution", default="")
    parser.add_argument("--output", default="sessions/event_trace_13i3")
    parser.add_argument("--machine", default="HOME")
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    frames_dir = Path(args.frames_dir) if args.frames_dir else None
    if frames_dir is None:
        candidates = sorted(
            Path("sessions").glob("13i3_*"), reverse=True
        )
        for candidate in candidates:
            if (candidate / "frames").is_dir():
                frames_dir = candidate / "frames"
                break
    if frames_dir is None or not frames_dir.is_dir():
        print("NO FRAMES DIR")
        return 1
    frames = _collect_frames(frames_dir)
    if not frames:
        print("NO SAMPLES")
        return 1
    registry = VisionProfileRegistry()
    profile = registry.get(args.profile)
    client_width, client_height = parse_resolution(
        args.client_resolution or (profile.resolution if profile else "")
    )
    pixel_rois = (
        resolve_pixel_rois_for(
            registry,
            args.profile,
            client_width=client_width,
            client_height=client_height,
        )
        if profile and client_width > 0
        else {}
    )
    hp_roi = pixel_rois.get("hp", {})
    mp_roi = pixel_rois.get("mp", {})
    map_roi = pixel_rois.get("map_label", {})
    rois = {"map_label": map_roi, "hp": hp_roi, "mp": mp_roi}

    scheduler = VisionScheduler()
    detector = FrameChangeDetector()
    extractor = HpMpGeometryExtractor()
    library = MapleVisualTemplateLibrary(
        manifest_path=output / "template_manifest.json",
        local_dir=output / "templates",
    )
    if frames:
        library.add_template(
            template_id="map_label_trace",
            kind="map_label",
            image_path=frames[0],
        )

    trace: dict = {
        "schema_version": "1.0",
        "privacy": "LOCAL RAW - do not commit",
        "machine": args.machine,
        "segments": [],
        "summary": {},
    }
    ocr_triggers = 0
    geometry_triggers = 0
    template_triggers = 0
    ocr_skipped = 0

    def run_segment(name: str, provenance: str, image_paths: list[Path]) -> dict:
        nonlocal ocr_triggers, geometry_triggers, template_triggers, ocr_skipped
        segment = {
            "name": name,
            "provenance": provenance,
            "steps": [],
        }
        for index, path in enumerate(image_paths):
            change = detector.detect(
                str(path), frame_id=path.stem, rois=rois
            )
            tasks = scheduler.plan(
                change,
                hp_mp_roi_present=bool(hp_roi),
                map_roi_present=bool(map_roi),
                quest_roi_present=False,
                dialog_roi_present=False,
            )
            step = {
                "frame": path.name,
                "changed": change.changed,
                "roi_scores": change.roi_scores,
                "tasks": [
                    {
                        "roi": task.roi,
                        "method": task.method.value,
                        "reason": task.reason,
                    }
                    for task in tasks
                ],
                "processors": [],
            }
            for task in tasks:
                if task.method is PerceptionMethod.COLOR_GEOMETRY:
                    geometry_triggers += 1
                    geometry = extractor.extract(
                        str(path), hp_roi=hp_roi, mp_roi=mp_roi
                    )
                    step["processors"].append(
                        {
                            "method": "geometry",
                            "hp_ratio": geometry.hp_ratio,
                            "mp_ratio": geometry.mp_ratio,
                            "latency_ms": geometry.latency_ms,
                        }
                    )
                elif task.method is PerceptionMethod.TEMPLATE:
                    template_triggers += 1
                    match = library.match(
                        str(path), "map_label_trace", threshold=0.5
                    )
                    step["processors"].append(
                        {
                            "method": "template",
                            "score": match.score,
                            "matched": match.matched,
                            "latency_ms": match.latency_ms,
                        }
                    )
                elif task.method is PerceptionMethod.OCR:
                    ocr_triggers += 1
                    step["processors"].append(
                        {"method": "ocr", "triggered": True}
                    )
            if not any(
                task.method is PerceptionMethod.OCR for task in tasks
            ):
                ocr_skipped += 1
            segment["steps"].append(step)
        return segment

    # REAL idle:前 5 帧(静态,大概率无变化)
    idle_frames = frames[: min(5, len(frames))]
    trace["segments"].append(
        run_segment("idle", "REAL", idle_frames)
    )

    # FIXTURE HP/MP change:副本绘制条变化
    fixture_dir = output / "fixture"
    fixture_dir.mkdir(parents=True, exist_ok=True)
    hp_fixture = fixture_dir / "hp_change.png"
    mp_fixture = fixture_dir / "mp_change.png"
    map_fixture = fixture_dir / "map_change.png"
    if frames:
        _fixture_modify_hpmp(frames[0], hp_fixture, ratio=0.5, kind="hp")
        _fixture_modify_hpmp(frames[0], mp_fixture, ratio=0.4, kind="mp")
        _fixture_modify_map(frames[0], map_fixture)
        trace["segments"].append(
            run_segment("hp_mp_change", "FIXTURE", [hp_fixture, mp_fixture])
        )
        trace["segments"].append(
            run_segment("map_change", "FIXTURE", [map_fixture])
        )

    trace["summary"] = {
        "ocr_triggers": ocr_triggers,
        "geometry_triggers": geometry_triggers,
        "template_triggers": template_triggers,
        "ocr_skipped_frames": ocr_skipped,
        "selective_scheduling": ocr_skipped > 0,
    }
    sanitizer = BenchmarkPrivacySanitizer()
    safe = sanitizer.sanitize_report(trace)
    sanitizer.assert_safe(safe)
    BenchmarkPrivacySanitizer.write_local_raw(
        output / "event_trace_raw.json", trace
    )
    BenchmarkPrivacySanitizer.write_local_raw(
        output / "event_trace_public.json", safe
    )
    print(json.dumps(trace["summary"], ensure_ascii=False, indent=2))
    print(f"TRACE RAW: {output / 'event_trace_raw.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
