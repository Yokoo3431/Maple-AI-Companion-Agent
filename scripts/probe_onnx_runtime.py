"""ONNX Runtime 可行性探针(Phase 13-I.1,只读架构评估)。"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ONNX Runtime feasibility probe(只读)"
    )
    parser.add_argument("--output", default="sessions/onnx_probe")
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    report: dict = {
        "schema_version": "1.0",
        "provider": "onnxruntime",
        "runtime": "read-only feasibility",
    }
    try:
        import onnxruntime as ort  # type: ignore[import-not-found]
    except ImportError as exc:
        report["available"] = False
        report["reason"] = f"onnxruntime not installed: {exc}"
        report["recommendation"] = (
            "install in optional local environment before local detector "
            "integration; CI keeps onnxruntime optional"
        )
        (output / "onnx_probe.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0
    start = time.perf_counter()
    providers = ort.get_available_providers()
    import_ms = round((time.perf_counter() - start) * 1000, 2)
    session_options = ort.SessionOptions()
    report.update(
        {
            "available": True,
            "version": ort.__version__,
            "available_providers": providers,
            "has_gpu_provider": "CUDAExecutionProvider" in providers
            or "DmlExecutionProvider" in providers,
            "import_ms": import_ms,
            "session_options": {
                "intra_op_threads": session_options.intra_op_num_threads,
                "optimization_level": str(
                    session_options.graph_optimization_level
                ),
            },
            "note": (
                "inference latency requires a real model; this probe only "
                "validates runtime/EP availability"
            ),
        }
    )
    (output / "onnx_probe.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
