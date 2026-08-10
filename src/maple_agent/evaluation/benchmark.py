"""EvaluationBenchmark:读取 sessions trace,生成评估报告(只读)。"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from maple_agent.evaluation.evaluator import (
    DecisionEvaluator,
    ExecutionEvaluator,
    MemoryEvaluator,
    PlanEvaluator,
    ReflectionEvaluator,
)
from maple_agent.evaluation.metrics import overall_score
from maple_agent.evaluation.models import AgentMetrics, EvaluationResult
from maple_agent.logging_setup import new_id

logger = logging.getLogger("maple_agent.evaluation")


def _load_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else None
    except Exception as exc:
        logger.warning("trace 读取失败: %s (%s)", path, exc)
        return None


class EvaluationBenchmark:
    """自动读取 sessions/<trace_id>/ 下的 trace 并评估 Agent 质量。"""

    TRACE_FILES = (
        "vision.json",
        "knowledge_match.json",
        "decision_trace.json",
        "action_plan_trace.json",
        "execution_orchestration.json",
        "reflection_trace.json",
    )

    def __init__(
        self,
        sessions_dir: str | Path = "sessions",
    ) -> None:
        self.sessions_dir = Path(sessions_dir)
        self.last_result: EvaluationResult | None = None
        self.last_metrics: AgentMetrics | None = None
        self.last_trace_count: int = 0

    def run(self, trace_id: str) -> EvaluationResult:
        """评估单个 trace 并写入 evaluation_report.json。"""
        directory = self.sessions_dir / trace_id
        decision = _load_json(directory / "decision_trace.json") or {}
        plan = _load_json(directory / "action_plan_trace.json") or {}
        execution = (
            _load_json(directory / "execution_orchestration.json") or {}
        )
        reflection = _load_json(directory / "reflection_trace.json") or {}
        decision_comp = DecisionEvaluator().evaluate(decision)
        plan_comp = PlanEvaluator().evaluate(plan)
        execution_comp = ExecutionEvaluator().evaluate(execution)
        reflection_comp = ReflectionEvaluator().evaluate(reflection)
        memory_comp = MemoryEvaluator().evaluate(decision)
        result = EvaluationResult(
            evaluation_id=new_id(),
            trace_id=trace_id,
            decision_score=decision_comp.score,
            planning_score=plan_comp.score,
            execution_score=execution_comp.score,
            reflection_score=reflection_comp.score,
            memory_score=memory_comp.score,
            overall_score=overall_score(
                decision_comp.score,
                plan_comp.score,
                execution_comp.score,
                reflection_comp.score,
                memory_comp.score,
            ),
            issues=(
                decision_comp.issues
                + plan_comp.issues
                + execution_comp.issues
                + reflection_comp.issues
                + memory_comp.issues
            ),
            recommendations=(
                decision_comp.recommendations
                + plan_comp.recommendations
                + execution_comp.recommendations
                + reflection_comp.recommendations
                + memory_comp.recommendations
            ),
        )
        self.last_result = result
        self._write_report(directory, result)
        logger.info(
            "evaluation: trace=%s overall=%.4f issues=%d",
            trace_id,
            result.overall_score,
            len(result.issues),
        )
        return result

    def benchmark(self) -> AgentMetrics:
        """扫描全部 trace 目录,汇总 AgentMetrics。"""
        results: list[EvaluationResult] = []
        replan_count = 0
        confidence_sum = 0.0
        confidence_count = 0
        for directory in sorted(self.sessions_dir.iterdir()):
            if not directory.is_dir():
                continue
            if not (directory / "decision_trace.json").exists():
                continue
            result = self.run(directory.name)
            results.append(result)
            reflection = _load_json(directory / "reflection_trace.json") or {}
            if reflection.get("trigger") == "REPLAN_REQUIRED":
                replan_count += 1
            confidence = (reflection.get("analysis") or {}).get("confidence")
            if confidence is not None:
                confidence_sum += float(confidence)
                confidence_count += 1
        if not results:
            metrics = AgentMetrics(overall_score=0.0)
            self.last_metrics = metrics
            self.last_trace_count = 0
            return metrics
        count = len(results)
        self.last_trace_count = count
        metrics = AgentMetrics(
            decision_accuracy=round(
                sum(r.decision_score for r in results) / count, 4
            ),
            plan_valid_rate=round(
                sum(r.planning_score for r in results) / count, 4
            ),
            execution_success_rate=round(
                sum(r.execution_score for r in results) / count, 4
            ),
            reflection_accuracy=round(
                sum(r.reflection_score for r in results) / count, 4
            ),
            experience_hit_rate=round(
                sum(r.memory_score for r in results) / count, 4
            ),
            replan_rate=round(replan_count / count, 4),
            average_confidence=round(
                confidence_sum / confidence_count, 4
            )
            if confidence_count
            else 0.0,
            overall_score=round(
                sum(r.overall_score for r in results) / count, 4
            ),
        )
        self.last_metrics = metrics
        logger.info(
            "benchmark: traces=%d overall=%.4f",
            count,
            metrics.overall_score,
        )
        return metrics

    def _write_report(
        self,
        directory: Path,
        result: EvaluationResult,
    ) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        payload = {
            "trace_id": result.trace_id,
            "metrics": {
                "decision": result.decision_score,
                "planning": result.planning_score,
                "execution": result.execution_score,
                "reflection": result.reflection_score,
                "experience": result.memory_score,
            },
            "scores": result.model_dump(mode="json"),
            "issues": result.issues,
            "recommendations": result.recommendations,
            "overall": result.overall_score,
        }
        (directory / "evaluation_report.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
