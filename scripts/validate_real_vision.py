"""Real Vision 只读 Client Benchmark(Phase 13-I)。

流程:窗口发现 -> 截图(ImageGrab,真实可运行 fallback) -> OCR(真实 backend)
      -> ROI 裁剪 OCR -> dataset manifest(LOCAL ONLY) -> benchmark -> readiness。
只读工具,禁止任何输入控制。未运行 Maple 客户端时明确输出
REAL CLIENT NOT AVAILABLE,不 crash、不伪造。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from maple_agent.logging_setup import new_id  # noqa: E402
from maple_agent.real_vision import (  # noqa: E402
    RealOCRProvider,
    RealVisionBenchmark,
    RealVisionBenchmarkResult,
    VisionGroundTruth,
    VisionValidationDataset,
    VisionValidationSample,
    WindowsScreenshotProvider,
    build_real_vision_client_benchmark_report,
    build_real_vision_readiness,
    load_vision_profiles,
    save_real_vision_client_benchmark,
    save_real_vision_validation_trace,
)
from maple_agent.vision_runtime.detector import VisionDetector  # noqa: E402
from maple_agent.vision_runtime.models import VisionFrame  # noqa: E402
from maple_agent.vision_runtime.parser import GameStateParser  # noqa: E402

ROI_NAMES = ("map_label", "hp", "mp", "quest", "dialog")


def _black_frame(path: Path) -> bool:
    """低亮度/低方差 -> BLACK_FRAME(避免把黑帧当成功截图)。"""
    try:
        from PIL import Image, ImageStat

        image = Image.open(path).convert("L")
        stats = ImageStat.Stat(image)
        mean = stats.mean[0]
        stddev = stats.stddev[0]
        return mean < 5.0 or stddev < 6.0
    except Exception:
        return False


def _parse_hp_mp_ratio(text: str) -> float | None:
    """从 ROI OCR 文本解析 HP/MP 比例:支持 `cur/max` 与 `nn%`。"""
    if not text:
        return None
    fraction = re.search(r"(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)", text)
    if fraction:
        current, maximum = float(fraction.group(1)), float(fraction.group(2))
        if maximum > 0:
            return round(min(1.0, max(0.0, current / maximum)), 4)
    percent = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
    if percent:
        raw = float(percent.group(1))
        return round(min(1.0, max(0.0, raw / 100 if raw > 1 else raw)), 4)
    return None


def _ocr_crop(
    ocr: RealOCRProvider,
    image_path: Path,
    roi: dict,
    index: int,
    name: str,
    samples_dir: Path,
) -> tuple[str, float, float]:
    """裁剪 ROI 并 OCR;返回 (text, confidence, latency_ms)。"""
    try:
        from PIL import Image

        box = (
            int(roi.get("x", 0)),
            int(roi.get("y", 0)),
            int(roi.get("x", 0)) + int(roi.get("width", 0)),
            int(roi.get("y", 0)) + int(roi.get("height", 0)),
        )
        crop = Image.open(image_path).crop(box)
        crop_path = samples_dir / f"roi_{name}_{index:03d}.png"
        crop.save(crop_path)
        start = time.perf_counter()
        frame = VisionFrame(
            frame_id=new_id(),
            source="IMAGE_REFERENCE",
            image_reference=str(crop_path),
        )
        result = ocr.recognize(frame)
        latency = round((time.perf_counter() - start) * 1000, 2)
        return result.text.strip(), result.confidence, latency
    except Exception:
        return "", 0.0, 0.0


def _predict_from_observation(
    observation,
    roi_map_text: str,
    roi_hp: float | None,
    roi_mp: float | None,
    ocr_confidence: float,
) -> dict:
    """把解析观察映射为 benchmark 期望的预测 dict。"""
    if observation is None:
        return {
            "visible_map": "",
            "visible_entities": [],
            "hp_reference": None,
            "mp_reference": None,
            "quest_state": "",
            "ui_elements": [],
            "confidence": 0.0,
            "ocr_ok": False,
        }
    return {
        "visible_map": roi_map_text or observation.visible_map,
        "visible_entities": [
            {"name": name, "type": "UNKNOWN"}
            for name in observation.visible_entities
        ],
        "hp_reference": (
            roi_hp if roi_hp is not None else observation.hp_reference
        ),
        "mp_reference": (
            roi_mp if roi_mp is not None else observation.mp_reference
        ),
        "quest_state": observation.quest_reference[0]
        if observation.quest_reference
        else "",
        "ui_elements": list(observation.ui_elements),
        "confidence": round(ocr_confidence, 4),
        "ocr_ok": bool(roi_map_text or observation.visible_map),
    }


def _write_no_client_trace(output: Path, trace_id: str, window_title: str) -> None:
    """真实客户端不存在时的诚实 trace(沿用 Phase 13-F 结构)。"""
    metrics = RealVisionBenchmarkResult(sample_count=0)
    readiness = build_real_vision_readiness(
        metrics,
        real_client_tested=False,
        capture_provider="windows",
        ocr_provider="none",
        capture_available=False,
        ocr_available=False,
    )
    save_real_vision_validation_trace(
        output,
        trace_id,
        provider={
            "capture_provider": "windows",
            "ocr_provider": "none",
            "binding": "NOT_FOUND",
        },
        window={"title": window_title},
        dataset={"sample_count": 0},
        metrics=metrics,
        readiness=readiness.model_dump(mode="json"),
        validation="NOT_READY",
    )


def _evaluate_and_report(
    *,
    output: Path,
    trace_id: str,
    dataset_dir: Path,
    samples: list[VisionValidationSample],
    observations: dict[str, dict],
    capture_latencies: list[float] | None = None,
    ocr_latencies: list[float] | None = None,
    e2e_latencies: list[float] | None = None,
    capture_ok: int = 0,
    taxonomy: dict[str, int] | None = None,
    failures: list[dict] | None = None,
    window_info: dict,
    binding: str,
    provider_method: str,
    provider_fallback: str,
    capability: dict,
    ground_truth_file: str,
) -> int:
    """基于样本与预测计算 benchmark、readiness 并输出报告。"""
    dataset = VisionValidationDataset(samples)
    benchmark = RealVisionBenchmark()
    metrics = benchmark.evaluate(
        samples,
        lambda sample: observations.get(
            sample.sample_id,
            _predict_from_observation(None, "", None, None, 0.0),
        ),
        capture_latencies_ms=capture_latencies,
        ocr_latencies_ms=ocr_latencies,
        e2e_latencies_ms=e2e_latencies,
        capture_success_rate=(
            round(capture_ok / max(1, len(samples)), 4)
            if capture_latencies
            else None
        ),
        ocr_success_rate=(
            round(
                sum(
                    1
                    for prediction in observations.values()
                    if prediction.get("ocr_ok")
                )
                / max(1, len(observations)),
                4,
            )
            if observations
            else None
        ),
        failure_taxonomy=dict(taxonomy or {}),
    )
    readiness = build_real_vision_readiness(
        metrics,
        real_client_tested=True,
        capture_provider=f"windows/{provider_method}",
        ocr_provider=capability.get("backend", "tesseract"),
    )
    report = build_real_vision_client_benchmark_report(
        machine_profile={
            "host": "home-pc",
            "os": "Windows",
            "display_scaling": window_info.get("dpi_scale", 1.0),
            "client_resolution": window_info.get("resolution", ""),
            "window_mode": window_info.get("window_mode", ""),
        },
        window=window_info,
        capture={
            "method": provider_method,
            "fallback_reason": provider_fallback,
            "status": binding,
        },
        ocr=capability,
        dataset={
            "sample_count": dataset.count(),
            "manifest": str(dataset_dir / "manifest.json"),
            "suggested_labels": str(dataset_dir / "suggested_labels.json"),
            "ground_truth_file": ground_truth_file or "",
        },
        metrics=metrics,
        readiness=readiness,
        failures=list(failures or []),
    )
    benchmark_path = save_real_vision_client_benchmark(
        output, trace_id, report
    )
    save_real_vision_validation_trace(
        output,
        trace_id,
        provider={
            "capture_provider": f"windows/{provider_method}",
            "ocr_provider": capability.get("backend", "none"),
            "binding": binding,
            "method": provider_method,
            "fallback_reason": provider_fallback,
        },
        window=window_info,
        dataset={"sample_count": dataset.count()},
        metrics=metrics,
        readiness=readiness.model_dump(mode="json"),
        validation=readiness.validation_status.value,
    )
    print("RealVisionReadiness =", readiness.validation_status.value)
    print("real_client_tested =", readiness.real_client_tested)
    print("samples =", dataset.count())
    print("capture_success =", metrics.capture_success_rate)
    print("ocr_success =", metrics.ocr_success_rate)
    print("capture_latency_ms =", metrics.mean_capture_latency_ms)
    print("ocr_latency_ms =", metrics.mean_ocr_latency_ms)
    print("map_accuracy =", metrics.map_accuracy)
    print("hp_mae =", metrics.hp_mae, "mp_mae =", metrics.mp_mae)
    print("quest_state_accuracy =", metrics.quest_state_accuracy)
    print("failure_taxonomy =", json.dumps(metrics.failure_taxonomy))
    print(
        "confidence_calibration =",
        metrics.confidence_calibration_status,
    )
    print(f"BENCHMARK: {benchmark_path}")
    print(
        f"TRACE: {output / trace_id / 'real_vision_validation_trace.json'}"
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Real Vision 只读 Client Benchmark(Phase 13-I)"
    )
    parser.add_argument("--window-title", default="MapleStory")
    parser.add_argument("--profile", default="default-800x600")
    parser.add_argument("--frames", type=int, default=20)
    parser.add_argument("--interval", type=float, default=0.5)
    parser.add_argument(
        "--output",
        default="sessions",
        help="trace 输出目录",
    )
    parser.add_argument(
        "--dataset-dir",
        default="",
        help="dataset manifest 输出目录(默认 <output>/<trace>/dataset)",
    )
    parser.add_argument(
        "--capture-samples",
        type=int,
        default=0,
        help="额外只采集帧数(不 OCR,用于 dataset 扩充)",
    )
    parser.add_argument(
        "--ground-truth",
        default="",
        help="ground truth JSON: {sample_id: {map_name,hp,mp,...}}",
    )
    parser.add_argument(
        "--ocr-lang",
        default="chi_sim+eng",
        help="Tesseract 语言(默认 chi_sim+eng)",
    )
    parser.add_argument(
        "--evaluate-manifest",
        default="",
        help="复用已有 dataset manifest 评估(不重新采集)",
    )
    args = parser.parse_args()
    if args.evaluate_manifest:
        manifest_path = Path(args.evaluate_manifest)
        dataset = VisionValidationDataset.from_manifest(manifest_path)
        dataset_dir = manifest_path.parent
        trace_id = str(dataset.manifest.get("trace_id", new_id()))
        output = Path(args.output)
        suggested_path = dataset_dir / "suggested_labels.json"
        suggested = (
            json.loads(suggested_path.read_text(encoding="utf-8"))
            if suggested_path.is_file()
            else {}
        )
        observations: dict[str, dict] = {}
        for sample_id, labels in suggested.items():
            observations[sample_id] = {
                "visible_map": labels.get("map_name_suggested", ""),
                "visible_entities": [],
                "hp_reference": labels.get("hp_suggested"),
                "mp_reference": labels.get("mp_suggested"),
                "quest_state": "",
                "ui_elements": [],
                "confidence": labels.get("confidence", 0.0),
                "ocr_ok": bool(labels.get("map_name_suggested", "")),
            }
        ground_truth_data: dict = {}
        if args.ground_truth:
            gt_path = Path(args.ground_truth)
            if gt_path.is_file():
                ground_truth_data = json.loads(
                    gt_path.read_text(encoding="utf-8")
                )
        for sample in dataset.samples:
            gt = ground_truth_data.get(
                sample.sample_id, ground_truth_data.get("*", {})
            )
            sample.ground_truth = VisionGroundTruth(
                map_name=gt.get("map_name", ""),
                aliases=gt.get("aliases", []),
                hp=gt.get("hp"),
                mp=gt.get("mp"),
                visible_npcs=gt.get("visible_npcs", []),
                visible_monsters=gt.get("visible_monsters", []),
                visible_items=gt.get("visible_items", []),
                quest_state=gt.get("quest_state", ""),
                ui_signals=gt.get("ui_signals", []),
            )
        capability = RealOCRProvider().capability()
        window_info = {
            "binding": "BOUND",
            "window_title": dataset.manifest.get("window_title", ""),
            "resolution": dataset.manifest.get("resolution", ""),
            "window_mode": dataset.manifest.get("window_mode", ""),
        }
        return _evaluate_and_report(
            output=output,
            trace_id=trace_id,
            dataset_dir=dataset_dir,
            samples=dataset.samples,
            observations=observations,
            window_info=window_info,
            binding="BOUND",
            provider_method=dataset.manifest.get(
                "capture_method", "imagegrab"
            ),
            provider_fallback="re-evaluated from existing dataset",
            capability=capability,
            ground_truth_file=args.ground_truth,
        )

    trace_id = new_id()
    output = Path(args.output)
    dataset_dir = (
        Path(args.dataset_dir)
        if args.dataset_dir
        else output / trace_id / "dataset"
    )
    samples_dir = output / trace_id / "vision_samples"
    samples_dir.mkdir(parents=True, exist_ok=True)

    profiles = load_vision_profiles()
    profile = profiles.get(args.profile)
    provider = WindowsScreenshotProvider(
        window_title=args.window_title,
        save_dir=str(samples_dir),
    )
    window_info = provider.discover_window()
    binding = window_info.get("binding", provider.binding_status())
    print(f"WINDOW_BINDING: {binding}")
    if window_info:
        for key in (
            "requested_title",
            "window_title",
            "hwnd",
            "pid",
            "process_name",
            "class_name",
            "resolution",
            "dpi_scale",
            "window_mode",
            "visible",
            "minimized",
            "foreground",
        ):
            value = window_info.get(key)
            if value not in (None, "", 0, False):
                print(f"WINDOW {key}: {value}")
    if binding == "NOT_FOUND":
        print("REAL CLIENT NOT AVAILABLE")
        metrics = RealVisionBenchmarkResult(sample_count=0)
        readiness = build_real_vision_readiness(
            metrics,
            real_client_tested=False,
            capture_provider="windows",
            ocr_provider="none",
            capture_available=False,
            ocr_available=False,
        )
        print(
            "RealVisionReadiness =",
            readiness.validation_status.value,
        )
        _write_no_client_trace(output, trace_id, args.window_title)
        print(
            f"TRACE: {output / trace_id / 'real_vision_validation_trace.json'}"
        )
        return 0

    ocr = RealOCRProvider()
    capability = ocr.capability()
    print(
        "OCR backend:",
        capability.get("backend"),
        "available =",
        capability.get("available"),
        "version =",
        capability.get("version", ""),
    )
    print(
        "OCR languages:",
        capability.get("languages", []),
        "chinese_support =",
        capability.get("chinese_support", False),
        "english_support =",
        capability.get("english_support", False),
    )
    if not ocr.available:
        print("OCR PROVIDER UNAVAILABLE")
        metrics = RealVisionBenchmarkResult(
            sample_count=0,
            failure_taxonomy={"OCR_UNAVAILABLE": 1},
        )
        readiness = build_real_vision_readiness(
            metrics,
            real_client_tested=True,
            capture_provider="windows",
            ocr_provider=ocr.backend_name,
            capture_available=True,
            ocr_available=False,
        )
        print(
            "RealVisionReadiness =",
            readiness.validation_status.value,
        )
        return 0

    roi_profile = profile.model_dump(mode="json") if profile else {}
    if profile and profile.resolution != window_info.get("resolution", ""):
        print(
            "WARNING: profile",
            args.profile,
            "resolution",
            profile.resolution,
            "!= window resolution",
            window_info.get("resolution", ""),
            "-> ROI_MISMATCH 风险",
        )

    capture_latencies: list[float] = []
    ocr_latencies: list[float] = []
    e2e_latencies: list[float] = []
    observations: dict[str, dict] = {}
    roi_results: dict[str, dict] = {}
    samples: list[VisionValidationSample] = []
    failures: list[dict] = []
    taxonomy: dict[str, int] = {}
    capture_ok = 0

    def record_failure(failure_type: str, message: str) -> None:
        failures.append({"type": failure_type, "message": message})
        taxonomy[failure_type] = taxonomy.get(failure_type, 0) + 1

    def capture_one(*, do_ocr: bool, index: int) -> VisionFrame | None:
        nonlocal capture_ok
        start = time.perf_counter()
        frame = provider.capture(trace_id=trace_id)
        capture_ms = round((time.perf_counter() - start) * 1000, 2)
        capture_latencies.append(capture_ms)
        status_ok = provider.last_status.value == "OK"
        if status_ok:
            capture_ok += 1
        else:
            record_failure(
                "CAPTURE_FAILED"
                if provider.last_status.value == "CAPTURE_FAILED"
                else "WINDOW_NOT_FOUND",
                provider.fallback_reason or provider.last_status.value,
            )
        win_state = dict(provider.last_window_info)
        image_path = Path(frame.image_reference)
        if status_ok and image_path.is_file():
            if _black_frame(image_path):
                record_failure("BLACK_FRAME", str(image_path))
        if do_ocr and status_ok and image_path.is_file():
            ocr_start = time.perf_counter()
            ocr_result = ocr.recognize(frame)
            ocr_ms = round((time.perf_counter() - ocr_start) * 1000, 2)
            ocr_latencies.append(ocr_ms)
            roi_map_text = ""
            roi_hp: float | None = None
            roi_mp: float | None = None
            if profile:
                roi_map = {
                    name: roi_profile.get(f"{name}_roi")
                    for name in ROI_NAMES
                }
                for name, roi in roi_map.items():
                    if not roi:
                        continue
                    text, _confidence, _latency = _ocr_crop(
                        ocr,
                        image_path,
                        roi,
                        index,
                        name,
                        samples_dir,
                    )
                    roi_results.setdefault(name, []).append(
                        {"text": text, "latency_ms": _latency}
                    )
                    if name == "map_label" and text:
                        roi_map_text = text
                    elif name == "hp":
                        roi_hp = _parse_hp_mp_ratio(text)
                    elif name == "mp":
                        roi_mp = _parse_hp_mp_ratio(text)
            elements = VisionDetector().detect(frame, ocr_result)
            observation = GameStateParser().parse(
                frame,
                ocr_result,
                elements,
            )
            if not ocr_result.text.strip() and not roi_map_text:
                record_failure("OCR_EMPTY", f"frame {index} empty OCR")
            if ocr_result.confidence < 0.5 and ocr_result.text.strip():
                record_failure(
                    "OCR_LOW_CONFIDENCE",
                    f"frame {index} confidence {ocr_result.confidence}",
                )
            observations[frame.frame_id] = _predict_from_observation(
                observation,
                roi_map_text,
                roi_hp,
                roi_mp,
                ocr_result.confidence,
            )
            roi_results.setdefault("full_frame", []).append(
                {
                    "text": ocr_result.text.strip(),
                    "confidence": ocr_result.confidence,
                    "latency_ms": ocr_ms,
                }
            )
        elif do_ocr and status_ok:
            record_failure("OCR_UNAVAILABLE", "image file missing for OCR")
        resolution = win_state.get("resolution", "")
        if (
            profile
            and profile.resolution
            and resolution
            and profile.resolution != resolution
        ):
            record_failure(
                "DPI_PROFILE_MISMATCH",
                f"profile {profile.resolution} != window {resolution}",
            )
        sample = VisionValidationSample(
            sample_id=frame.frame_id,
            source_type="real",
            game_profile=profile.game_profile if profile else "",
            server_profile=profile.server_profile if profile else "",
            resolution=resolution,
            window_mode=win_state.get("window_mode", ""),
            dpi_scale=float(win_state.get("dpi_scale", 1.0) or 1.0),
            image_reference=str(image_path),
            captured_at=frame.timestamp,
            notes=(
                "foreground"
                if win_state.get("foreground")
                else "occluded-or-background"
            ),
        )
        samples.append(sample)
        e2e_latencies.append(
            round((time.perf_counter() - start) * 1000, 2)
        )
        return frame

    for index in range(max(1, args.frames)):
        capture_one(do_ocr=True, index=index)
        time.sleep(max(0.0, args.interval))
    for index in range(args.capture_samples):
        capture_one(do_ocr=False, index=args.frames + index)
        time.sleep(max(0.0, args.interval))

    record_failure(
        "UNSUPPORTED_ENTITY_VISION",
        "no real CV detector for NPC/Monster/Item; knowledge is not vision",
    )

    ground_truth_data: dict = {}
    if args.ground_truth:
        gt_path = Path(args.ground_truth)
        if gt_path.is_file():
            ground_truth_data = json.loads(
                gt_path.read_text(encoding="utf-8")
            )
    for sample in samples:
        gt = ground_truth_data.get(
            sample.sample_id, ground_truth_data.get("*", {})
        )
        sample.ground_truth = VisionGroundTruth(
            map_name=gt.get("map_name", ""),
            aliases=gt.get("aliases", []),
            hp=gt.get("hp"),
            mp=gt.get("mp"),
            visible_npcs=gt.get("visible_npcs", []),
            visible_monsters=gt.get("visible_monsters", []),
            visible_items=gt.get("visible_items", []),
            quest_state=gt.get("quest_state", ""),
            ui_signals=gt.get("ui_signals", []),
        )

    dataset = VisionValidationDataset(samples)
    dataset.manifest = {
        "trace_id": trace_id,
        "source": "real-client",
        "window_title": window_info.get("window_title", args.window_title),
        "hwnd": window_info.get("hwnd"),
        "profile": args.profile,
        "capture_method": provider.capture_method,
        "game_profile": profile.game_profile if profile else "",
        "server_profile": profile.server_profile if profile else "",
        "resolution": window_info.get("resolution", ""),
        "collected_at": datetime.now(UTC).isoformat(),
    }
    dataset.save_manifest(dataset_dir / "manifest.json")
    suggested = {
        sample_id: {
            "map_name_suggested": (
                observations.get(sample_id, {}).get("visible_map", "")
            ),
            "hp_suggested": observations.get(sample_id, {}).get(
                "hp_reference"
            ),
            "mp_suggested": observations.get(sample_id, {}).get(
                "mp_reference"
            ),
            "confidence": observations.get(sample_id, {}).get(
                "confidence", 0.0
            ),
        }
        for sample_id in observations
    }
    (dataset_dir / "suggested_labels.json").write_text(
        json.dumps(suggested, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return _evaluate_and_report(
        output=output,
        trace_id=trace_id,
        dataset_dir=dataset_dir,
        samples=samples,
        observations=observations,
        capture_latencies=capture_latencies,
        ocr_latencies=ocr_latencies,
        e2e_latencies=e2e_latencies,
        capture_ok=capture_ok,
        taxonomy=taxonomy,
        failures=failures,
        window_info=window_info,
        binding=binding,
        provider_method=provider.capture_method,
        provider_fallback=provider.fallback_reason,
        capability=capability,
        ground_truth_file=args.ground_truth,
    )


if __name__ == "__main__":
    raise SystemExit(main())
