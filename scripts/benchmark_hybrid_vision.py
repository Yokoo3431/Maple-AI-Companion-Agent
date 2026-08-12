"""Hybrid Local Perception Benchmark(Phase 13-I.1,真实本地样本,只读)。

逐 provider 测量:change detection / HP-MP geometry / template / Tesseract ROI /
knowledge resolution;输出 LOCAL RAW 报告 + repository-safe 摘要。
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from maple_agent.hybrid_vision import (  # noqa: E402
    BenchmarkPrivacySanitizer,
    ChangeDetectorBenchmark,
    FrameChangeDetector,
    HpMpGeometryExtractor,
    KnowledgeGuidedResolver,
    MapleVisualTemplateLibrary,
)
from maple_agent.maple_knowledge import (  # noqa: E402
    MapleKnowledgeGraph,
    load_demo_knowledge,
)
from maple_agent.real_vision import (  # noqa: E402
    RealOCRProvider,
    load_vision_profiles,
)


def _latency_stats(values: list[float]) -> dict:
    if not values:
        return {"mean_ms": None, "p50_ms": None, "p95_ms": None, "max_ms": None}
    ordered = sorted(values)
    return {
        "mean_ms": round(statistics.mean(values), 3),
        "p50_ms": round(statistics.median(values), 3),
        "p95_ms": round(
            ordered[max(0, int(0.95 * len(ordered)) - 1)], 3
        ),
        "max_ms": round(ordered[-1], 3),
    }


def _load_samples(manifest_path: Path) -> list[Path]:
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    repo_root = Path(__file__).resolve().parents[1]
    frames: list[Path] = []
    for sample in data.get("samples", []):
        reference = sample.get("image_reference", "")
        if reference and reference.startswith("sessions"):
            frames.append(repo_root / reference)
        elif reference and Path(reference).is_absolute():
            frames.append(Path(reference))
    return frames


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Hybrid Local Perception benchmark(只读,本地样本)"
    )
    parser.add_argument(
        "--manifest",
        default="sessions/bfb8ba450802/dataset/manifest.json",
        help="真实 dataset manifest(本地)",
    )
    parser.add_argument(
        "--profile", default="home_pc_2560x1440"
    )
    parser.add_argument(
        "--output", default="sessions/hybrid_benchmark_13i1"
    )
    parser.add_argument("--ground-truth-map", default="射手村")
    parser.add_argument(
        "--aliases",
        default="金银岛射手村,金银岛,Henesys",
        help="地图别名(逗号分隔)",
    )
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    manifest_path = Path(args.manifest)
    frames = _load_samples(manifest_path)
    if not frames:
        print("NO SAMPLES")
        return 1
    profiles = load_vision_profiles()
    profile = profiles.get(args.profile)
    if profile is None:
        print(f"PROFILE NOT FOUND: {args.profile}")
        return 1
    profile_data = profile.model_dump(mode="json")
    hp_roi = profile_data.get("hp_roi", {})
    mp_roi = profile_data.get("mp_roi", {})
    map_roi = profile_data.get("map_label_roi", {})
    aliases = [item.strip() for item in args.aliases.split(",") if item.strip()]

    # 1) change detection(连续帧)
    detector = FrameChangeDetector()
    change_bench = ChangeDetectorBenchmark.evaluate(
        frames[: max(1, len(frames) - 1)],
        rois={
            "map_label": map_roi,
            "hp": hp_roi,
            "mp": mp_roi,
        },
        detector=detector,
    )

    # 2) HP/MP geometry
    extractor = HpMpGeometryExtractor()
    hp_values: list[float | None] = []
    mp_values: list[float | None] = []
    hp_conf: list[float] = []
    mp_conf: list[float] = []
    hpmp_latencies: list[float] = []
    hpmp_failures = 0
    for path in frames:
        start = time.perf_counter()
        result = extractor.extract(
            str(path), hp_roi=hp_roi, mp_roi=mp_roi
        )
        hpmp_latencies.append(result.latency_ms or 0.0)
        hp_values.append(result.hp_ratio)
        mp_values.append(result.mp_ratio)
        hp_conf.append(result.hp_confidence)
        mp_conf.append(result.mp_confidence)
        if result.hp_ratio is None or result.mp_ratio is None:
            hpmp_failures += 1
    present_hp = [value for value in hp_values if value is not None]
    present_mp = [value for value in mp_values if value is not None]

    # 3) template: 用第一帧 map label crop 注册,匹配其余 crop
    library = MapleVisualTemplateLibrary(
        local_dir=output / "templates",
        manifest_path=output / "template_manifest.json",
    )
    template_source = None
    map_crops = sorted(
        (output.parent / "..").glob("**/roi_map_label_*.png")
    ) or sorted(
        Path("sessions").glob("**/roi_map_label_*.png")
    )
    template_consistency: list[float] = []
    template_latencies: list[float] = []
    if map_crops:
        library.add_template(
            template_id="map_label_henesys",
            kind="map_label",
            image_path=map_crops[0],
            version="1.0",
            notes="local map label template (Henesys/射手村)",
        )
        template_source = str(map_crops[0])
        for crop in map_crops[1:]:
            start = time.perf_counter()
            match = library.match(str(crop), "map_label_henesys")
            template_latencies.append(
                (time.perf_counter() - start) * 1000
            )
            template_consistency.append(match.score)

    # 4) Tesseract ROI baseline
    ocr = RealOCRProvider()
    ocr_capability = ocr.capability()
    map_ocr_texts: list[str] = []
    ocr_latencies: list[float] = []
    for crop in map_crops:
        from maple_agent.vision_runtime.models import VisionFrame

        frame = VisionFrame(
            frame_id=f"crop-{crop.stem}",
            source="IMAGE_REFERENCE",
            image_reference=str(crop),
        )
        start = time.perf_counter()
        result = ocr.recognize(frame)
        ocr_latencies.append((time.perf_counter() - start) * 1000)
        map_ocr_texts.append(result.text.strip())

    # 5) knowledge-guided resolution(OCR 证据 -> canonical)
    graph = MapleKnowledgeGraph()
    entities, relations = load_demo_knowledge()
    for entity in entities:
        graph.add_entity(entity)
    for relation in relations:
        graph.add_relation(relation)
    resolver = KnowledgeGuidedResolver(knowledge=graph)
    resolution_results = []
    for text in map_ocr_texts:
        resolution_results.append(
            resolver.resolve_name(
                text,
                evidence_confidence=0.5,
                candidates=[
                    {
                        "id": "map:henesys",
                        "name": args.ground_truth_map,
                        "aliases": aliases,
                    }
                ],
            ).model_dump(mode="json")
        )
    resolved_count = sum(
        1 for item in resolution_results if item["resolved"]
    )

    gt = args.ground_truth_map
    exact_hits = sum(1 for text in map_ocr_texts if text == gt)
    alias_hits = sum(
        1
        for text in map_ocr_texts
        if text in aliases
    )
    ocr_total = max(1, len(map_ocr_texts))

    report = {
        "schema_version": "1.0",
        "privacy": "LOCAL RAW - do not commit",
        "machine_profile": {
            "host": "home-pc",
            "resolution": profile_data.get("resolution", ""),
            "dpi_scale": profile_data.get("dpi_scale", 1.0),
        },
        "dataset": {
            "sample_count": len(frames),
            "manifest": str(manifest_path),
        },
        "providers": {
            "change_detector": {
                **change_bench,
                "samples": len(frames),
            },
            "hpmp_geometry": {
                "backend": extractor.backend,
                "hp_present": len(present_hp),
                "mp_present": len(present_mp),
                "hp_mean_ratio": (
                    round(statistics.mean(present_hp), 4)
                    if present_hp
                    else None
                ),
                "mp_mean_ratio": (
                    round(statistics.mean(present_mp), 4)
                    if present_mp
                    else None
                ),
                "hp_confidence_mean": (
                    round(statistics.mean(hp_conf), 4) if hp_conf else None
                ),
                "mp_confidence_mean": (
                    round(statistics.mean(mp_conf), 4) if mp_conf else None
                ),
                "failures": hpmp_failures,
                "latency": _latency_stats(hpmp_latencies),
            },
            "template": {
                "backend": library.backend,
                "template_source": template_source,
                "candidate_count": len(template_consistency),
                "mean_score": (
                    round(statistics.mean(template_consistency), 4)
                    if template_consistency
                    else None
                ),
                "min_score": (
                    round(min(template_consistency), 4)
                    if template_consistency
                    else None
                ),
                "latency": _latency_stats(template_latencies),
            },
            "tesseract_roi": {
                "backend": ocr_capability.get("backend", "none"),
                "available": ocr_capability.get("available", False),
                "samples": len(map_ocr_texts),
                "exact_accuracy": round(exact_hits / ocr_total, 4),
                "alias_accuracy": round(alias_hits / ocr_total, 4),
                "latency": _latency_stats(ocr_latencies),
            },
            "knowledge_resolution": {
                "samples": len(resolution_results),
                "resolved_count": resolved_count,
                "resolved_ratio": round(
                    resolved_count / max(1, len(resolution_results)), 4
                ),
                "fabrication_guard": (
                    "knowledge prior does not create observation"
                ),
            },
        },
        "metrics": {
            "map_ocr_exact_accuracy": round(exact_hits / ocr_total, 4),
            "map_ocr_alias_accuracy": round(alias_hits / ocr_total, 4),
            "map_template_consistency_mean": (
                round(statistics.mean(template_consistency), 4)
                if template_consistency
                else None
            ),
            "hp_mp_ground_truth": "100%/100% (user confirmed)",
        },
        "readiness": {
            "real_vision": "FOUNDATION_ONLY",
            "knowledge": "FOUNDATION_ONLY",
            "overall_controlled_execution": "NOT_READY",
        },
    }

    sanitizer = BenchmarkPrivacySanitizer()
    safe_report = sanitizer.sanitize_report(report)
    sanitizer.assert_safe(safe_report)
    raw_path = output / "hybrid_vision_benchmark_raw.json"
    safe_path = output / "hybrid_vision_benchmark_public.json"
    BenchmarkPrivacySanitizer.write_local_raw(raw_path, report)
    BenchmarkPrivacySanitizer.write_local_raw(safe_path, safe_report)
    print(json.dumps(safe_report, ensure_ascii=False, indent=2))
    print(f"LOCAL RAW: {raw_path}")
    print(f"REPOSITORY SAFE: {safe_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
