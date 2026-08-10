"""VisionBenchmark:视觉评测集运行(只读)。"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from maple_agent.observation.models import ObservationFrame, ObservationState
from maple_agent.vision_eval.evaluator import VisionEvaluator
from maple_agent.vision_eval.models import (
    VisionBenchmarkCase,
    VisionBenchmarkResult,
)

logger = logging.getLogger("maple_agent.vision_eval")


class VisionBenchmark:
    """加载评测集并对每个 case 运行 VisionEvaluator。"""

    def __init__(
        self,
        evaluator: VisionEvaluator,
        *,
        data_dir: str | Path | None = None,
        tolerance: float = 0.15,
    ) -> None:
        self.evaluator = evaluator
        self.data_dir = (
            Path(data_dir)
            if data_dir is not None
            else Path(__file__).resolve().parent / "data"
        )
        self.tolerance = tolerance

    def load_cases(self) -> list[VisionBenchmarkCase]:
        path = self.data_dir / "vision_benchmark_cases.json"
        if not path.exists():
            logger.warning("评测集不存在: %s", path)
            return []
        raw = json.loads(path.read_text(encoding="utf-8"))
        return [
            VisionBenchmarkCase.model_validate(item)
            for item in raw.get("cases", [])
        ]

    def run(self) -> VisionBenchmarkResult:
        cases = self.load_cases()
        if not cases:
            return VisionBenchmarkResult(
                total_cases=0,
                accuracy=0.0,
                average_score=0.0,
                failure_count=0,
            )
        passed = 0
        scores: list[float] = []
        failures: list[str] = []
        for case in cases:
            frame = ObservationFrame(
                frame_id=case.case_id,
                image_available=bool(case.ocr_text) or case.confidence > 0,
                ocr_text=case.ocr_text,
                confidence=case.confidence,
            )
            state = ObservationState(
                map_name=case.map_name,
                visible_entities=case.entities,
                confidence=case.confidence,
            )
            result = self.evaluator.evaluate(frame=frame, state=state)
            score_ok = (
                abs(result.overall_score - case.expected_score)
                <= self.tolerance
            )
            risk_ok = result.risk_level is case.expected_risk
            scores.append(result.overall_score)
            if score_ok and risk_ok:
                passed += 1
            else:
                failures.append(
                    f"{case.case_id}: score={result.overall_score}"
                    f"(exp {case.expected_score}) "
                    f"risk={result.risk_level.value}"
                    f"(exp {case.expected_risk.value})"
                )
        total = len(cases)
        result = VisionBenchmarkResult(
            total_cases=total,
            passed=passed,
            accuracy=round(passed / total, 4),
            average_score=round(sum(scores) / total, 4),
            failure_count=total - passed,
            failures=failures,
        )
        logger.info(
            "vision benchmark: cases=%d passed=%d accuracy=%.4f avg=%.4f",
            total,
            passed,
            result.accuracy,
            result.average_score,
        )
        return result
