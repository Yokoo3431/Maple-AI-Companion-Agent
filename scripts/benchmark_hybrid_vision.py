"""Hybrid Local Perception Benchmark(Phase 13-I.1/13-I.3,真实本地样本,只读)。

逐 provider 测量:change detection / HP-MP geometry / template discrimination /
Tesseract ROI / knowledge resolution;输出 LOCAL RAW 报告 + repository-safe 摘要。
支持 profile transform(GAME CLIENT 分辨率参数化)与 machine/provenance 标签。
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
    parse_resolution,
    resolve_pixel_rois_for,
)
from maple_agent.hybrid_vision.profile import VisionProfileRegistry  # noqa: E402
from maple_agent.maple_knowledge import (  # noqa: E402
    MapleKnowledgeGraph,
    load_demo_knowledge,
)
from maple_agent.real_vision import RealOCRProvider  # noqa: E402


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


def _collect_frames(frames_dir: Path) -> list[Path]:
    if not frames_dir.is_dir():
        return []
    return sorted(frames_dir.glob("*.png"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Hybrid Local Perception benchmark(只读,本地样本)"
    )
    parser.add_argument(
        "--frames-dir",
        default="",
        help="采集器输出 frames 目录(默认自动找最新 sessions/13i3_*)",
    )
    parser.add_argument(
        "--crops-dir",
        default="",
        help="map_label ROI 裁剪目录(默认 <frames-dir>/../roi/map_label)",
    )
    parser.add_argument(
        "--map-crops",
        default="",
        help="多地图判别:逗号分隔 'map_label=dir',例如 "
        "'射手村=sessions/13i3_home_foreground/roi/map_label,"
        "射手村集市=sessions/13i3_home_map_market/roi/map_label'",
    )
    parser.add_argument("--profile", default="home_pc_2560x1440")
    parser.add_argument(
        "--client-resolution", default="",
        help="GAME CLIENT 分辨率(默认取 profile.resolution)",
    )
    parser.add_argument(
        "--display-resolution", default="",
        help="显示器分辨率(仅元数据,非 transform 目标)",
    )
    parser.add_argument(
        "--machine", default="HOME", help="HOME / OFFICE / OTHER"
    )
    parser.add_argument(
        "--provenance",
        default="REAL_HOME",
        help="REAL_HOME / REAL_OFFICE / SYNTHETIC / N/A",
    )
    parser.add_argument(
        "--color-mode",
        default="red_blue",
        choices=("red_blue", "green"),
        help="HP/MP 条颜色模型:red_blue(默认)或 green(该 Unity 客户端)",
    )
    parser.add_argument(
        "--output", default="sessions/hybrid_benchmark_13i3"
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
    crops_dir = (
        Path(args.crops_dir)
        if args.crops_dir
        else frames_dir.parent / "roi" / "map_label"
    )
    registry = VisionProfileRegistry()
    profile = registry.get(args.profile)
    if profile is None:
        print(f"PROFILE NOT FOUND: {args.profile}")
        return 1
    client_width, client_height = parse_resolution(
        args.client_resolution or profile.resolution
    )
    if client_width <= 0 or client_height <= 0:
        print(
            f"INVALID CLIENT RESOLUTION: "
            f"{args.client_resolution or profile.resolution}"
        )
        return 1
    pixel_rois = resolve_pixel_rois_for(
        registry,
        args.profile,
        client_width=client_width,
        client_height=client_height,
    )
    hp_roi = pixel_rois.get("hp", {})
    mp_roi = pixel_rois.get("mp", {})
    map_roi = pixel_rois.get("map_label", {})
    aliases = [item.strip() for item in args.aliases.split(",") if item.strip()]
    display_resolution = (
        args.display_resolution or profile.display_resolution or ""
    )

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
        result = extractor.extract(
            str(path),
            hp_roi=hp_roi,
            mp_roi=mp_roi,
            color_mode=(
                "green"
                if args.color_mode == "green"
                else None
            ),
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

    # 3) template:单地图一致性 + 多地图判别
    library = MapleVisualTemplateLibrary(
        local_dir=output / "templates",
        manifest_path=output / "template_manifest.json",
    )
    map_crops = (
        sorted(crops_dir.glob("*.png")) if crops_dir.is_dir() else []
    )
    template_consistency: list[float] = []
    template_latencies: list[float] = []
    template_top1: dict | None = None
    template_margin: float | None = None
    template_unknown = 0
    template_correct = 0
    multi_map_top1_correct = 0
    multi_map_total = 0
    multi_map_unknown = 0
    multi_map_false_positive = 0
    multi_map_margins: list[float] = []
    multi_map_names: list[str] = []
    if map_crops and not args.map_crops:
        library.add_template(
            template_id=f"map_label_{args.machine.lower()}",
            kind="map_label",
            image_path=map_crops[0],
            version="1.0",
            notes=f"local map label template ({args.machine})",
        )
        for crop in map_crops[1:]:
            start = time.perf_counter()
            discrimination = library.discriminate(
                str(crop),
                kind="map_label",
                threshold=0.60,
                min_margin=0.05,
                query_id=crop.stem,
            )
            template_latencies.append(
                (time.perf_counter() - start) * 1000
            )
            template_consistency.append(
                discrimination.top1.score if discrimination.top1 else 0.0
            )
            if discrimination.matched:
                template_correct += 1
            else:
                template_unknown += 1
            if discrimination.top1 is not None:
                template_top1 = discrimination.top1.model_dump(mode="json")
                template_margin = discrimination.margin

    map_groups: list[tuple[str, list[Path]]] = []
    if args.map_crops:
        canonical_dir = output / "map_crops_canonical"
        canonical_dir.mkdir(parents=True, exist_ok=True)
        for pair in args.map_crops.split(","):
            pair = pair.strip()
            if "=" not in pair:
                continue
            label, directory = pair.split("=", 1)
            directory_path = Path(directory.strip())
            crops = (
                sorted(directory_path.glob("*.png"))
                if directory_path.is_dir()
                else []
            )
            if crops:
                # 跨分辨率归一化:统一 resize 后注册/匹配
                from PIL import Image

                label = label.strip()
                normalized_crops: list[Path] = []
                for index, crop in enumerate(crops):
                    target = canonical_dir / f"{label}_{index:03d}.png"
                    image = Image.open(crop).convert("L")
                    image = image.resize((300, 45), Image.LANCZOS)
                    image.save(target)
                    normalized_crops.append(target)
                map_groups.append((label, normalized_crops))
                multi_map_names.append(label)
    if len(map_groups) >= 2:
        # 注册每个地图模板(取各自首帧),判别所有地图的裁剪
        for label, crops in map_groups:
            library.add_template(
                template_id=f"map_{label}",
                kind="map_label",
                image_path=crops[0],
                version="1.0",
                notes=f"multi-map template {label}",
            )
        for label, crops in map_groups:
            for crop in crops[1:]:
                discrimination = library.discriminate(
                    str(crop),
                    kind="map_label",
                    threshold=0.60,
                    min_margin=0.05,
                    query_id=crop.stem,
                )
                multi_map_total += 1
                if not discrimination.matched:
                    multi_map_unknown += 1
                    continue
                if discrimination.top1 is not None:
                    multi_map_margins.append(discrimination.margin)
                top1_id = (
                    discrimination.top1.template_id
                    if discrimination.top1
                    else ""
                )
                if top1_id == f"map_{label}":
                    multi_map_top1_correct += 1
                else:
                    multi_map_false_positive += 1

    # 4) Tesseract ROI baseline(可选,依赖本机 tesseract)
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

    # 5) knowledge-guided resolution(OCR 证据 -> canonical,不伪造)
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
    alias_hits = sum(1 for text in map_ocr_texts if text in aliases)
    ocr_total = max(1, len(map_ocr_texts))
    multi_map = len(map_crops) >= 4

    report = {
        "schema_version": "1.0",
        "privacy": "LOCAL RAW - do not commit",
        "machine": args.machine,
        "provenance": args.provenance,
        "machine_profile": {
            "client_resolution": f"{client_width}x{client_height}",
            "display_resolution": display_resolution,
            "dpi_scale": profile.dpi_scale,
            "window_mode": profile.window_mode,
            "profile_transform_status": "OK",
        },
        "dataset": {
            "sample_count": len(frames),
            "frames_dir": str(frames_dir),
            "crops_dir": str(crops_dir),
        },
        "providers": {
            "change_detector": {
                **change_bench,
                "samples": len(frames),
            },
            "hpmp_geometry": {
                "backend": extractor.backend,
                "color_mode": args.color_mode,
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
                "candidate_count": len(template_consistency),
                "mean_score": (
                    round(statistics.mean(template_consistency), 4)
                    if template_consistency
                    else None
                ),
                "top1": template_top1,
                "margin": template_margin,
                "correct": template_correct,
                "unknown": template_unknown,
                "multi_map_evidence": multi_map,
                "multi_map_top1_correct": multi_map_top1_correct,
                "multi_map_total": multi_map_total,
                "multi_map_unknown": multi_map_unknown,
                "multi_map_false_positive": multi_map_false_positive,
                "multi_map_margin_mean": (
                    round(statistics.mean(multi_map_margins), 4)
                    if multi_map_margins
                    else None
                ),
                "multi_map_names": multi_map_names,
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
            "map_template_top1_accuracy": (
                round(template_correct / max(1, template_correct + template_unknown), 4)
                if (template_correct + template_unknown)
                else None
            ),
            "map_template_unknown_rate": (
                round(template_unknown / max(1, template_correct + template_unknown), 4)
                if (template_correct + template_unknown)
                else None
            ),
            "map_template_margin": template_margin,
            "real_multi_map_evidence": (
                "SUFFICIENT"
                if len(map_groups) >= 2 and multi_map_total > 0
                else "INSUFFICIENT"
            ),
            "multi_map_top1_accuracy": (
                round(
                    multi_map_top1_correct / max(1, multi_map_total), 4
                )
                if multi_map_total
                else None
            ),
            "multi_map_unknown_rate": (
                round(multi_map_unknown / max(1, multi_map_total), 4)
                if multi_map_total
                else None
            ),
            "multi_map_false_positive_rate": (
                round(
                    multi_map_false_positive / max(1, multi_map_total), 4
                )
                if multi_map_total
                else None
            ),
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
