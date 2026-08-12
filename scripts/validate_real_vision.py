"""Real Vision 只读 Smoke 验证:发现/绑定窗口 -> 截图 -> OCR -> 解析 -> 报告。

只读工具,禁止任何输入控制。
未运行 Maple 客户端时明确输出 REAL CLIENT NOT AVAILABLE,不 crash。
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from maple_agent.logging_setup import new_id  # noqa: E402
from maple_agent.real_vision import (  # noqa: E402
    RealOCRProvider,
    RealVisionBenchmarkResult,
    WindowsScreenshotProvider,
    build_real_vision_readiness,
    save_real_vision_validation_trace,
)
from maple_agent.vision_runtime.detector import VisionDetector  # noqa: E402
from maple_agent.vision_runtime.parser import GameStateParser  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Real Vision 只读验证(不输入游戏)"
    )
    parser.add_argument("--window-title", default="MapleStory")
    parser.add_argument("--profile", default="default-800x600")
    parser.add_argument("--frames", type=int, default=5)
    parser.add_argument("--interval", type=float, default=0.5)
    parser.add_argument(
        "--output",
        default="sessions",
        help="trace 输出目录",
    )
    args = parser.parse_args()
    trace_id = new_id()
    output = Path(args.output)
    provider = WindowsScreenshotProvider(
        window_title=args.window_title,
        save_dir=str(output / trace_id / "screenshots"),
    )
    binding = provider.binding_status()
    print(f"WINDOW_BINDING: {binding}")
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
        save_real_vision_validation_trace(
            output,
            trace_id,
            provider={
                "capture_provider": "windows",
                "ocr_provider": "none",
                "binding": binding,
            },
            window={"title": args.window_title},
            dataset={"sample_count": 0},
            metrics=metrics,
            readiness=readiness.model_dump(mode="json"),
            validation="NOT_READY",
        )
        print(f"TRACE: {output / trace_id / 'real_vision_validation_trace.json'}")
        return 0
    ocr = RealOCRProvider()
    if not ocr.available:
        print("OCR PROVIDER UNAVAILABLE")
        metrics = RealVisionBenchmarkResult(sample_count=0)
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
    capture_latencies: list[float] = []
    ocr_latencies: list[float] = []
    observations: list[dict] = []
    capture_ok = 0
    for _ in range(max(1, args.frames)):
        start = time.perf_counter()
        frame = provider.capture(trace_id=trace_id)
        capture_latencies.append(
            round((time.perf_counter() - start) * 1000, 2)
        )
        if provider.last_status.value == "OK":
            capture_ok += 1
            start = time.perf_counter()
            ocr_result = ocr.recognize(frame)
            ocr_latencies.append(
                round((time.perf_counter() - start) * 1000, 2)
            )
            elements = VisionDetector().detect(frame, ocr_result)
            observation = GameStateParser().parse(
                frame,
                ocr_result,
                elements,
            )
            observations.append(observation.model_dump(mode="json"))
        time.sleep(max(0.0, args.interval))
    metrics = RealVisionBenchmarkResult(
        sample_count=len(observations),
        capture_success_rate=(
            round(capture_ok / max(1, args.frames), 4)
        ),
        ocr_success_rate=(
            round(len(observations) / max(1, args.frames), 4)
        ),
        mean_capture_latency_ms=(
            round(sum(capture_latencies) / len(capture_latencies), 2)
            if capture_latencies
            else None
        ),
        mean_ocr_latency_ms=(
            round(sum(ocr_latencies) / len(ocr_latencies), 2)
            if ocr_latencies
            else None
        ),
    )
    readiness = build_real_vision_readiness(
        metrics,
        real_client_tested=True,
        capture_provider="windows",
        ocr_provider=ocr.backend_name,
    )
    print(
        "RealVisionReadiness =",
        readiness.validation_status.value,
    )
    print(
        "capture_success =",
        metrics.capture_success_rate,
        "ocr_success =",
        metrics.ocr_success_rate,
    )
    print(
        "capture_latency_ms =",
        metrics.mean_capture_latency_ms,
        "ocr_latency_ms =",
        metrics.mean_ocr_latency_ms,
    )
    print("observations =", len(observations))
    save_real_vision_validation_trace(
        output,
        trace_id,
        provider={
            "capture_provider": "windows",
            "ocr_provider": ocr.backend_name,
            "binding": binding,
            "method": provider.capture_method,
            "fallback_reason": provider.fallback_reason,
        },
        window={"title": args.window_title},
        dataset={"sample_count": len(observations)},
        metrics=metrics,
        readiness=readiness.model_dump(mode="json"),
        validation=readiness.validation_status.value,
    )
    print(
        f"TRACE: {output / trace_id / 'real_vision_validation_trace.json'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
