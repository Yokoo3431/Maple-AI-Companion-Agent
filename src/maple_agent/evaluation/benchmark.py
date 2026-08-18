"""EvaluationBenchmark:读取 sessions trace,生成评估报告(只读)。"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from maple_agent.context_reasoning.models import ContextType
from maple_agent.context_reasoning.reasoner import ContextReasoner
from maple_agent.evaluation.evaluator import (
    DecisionEvaluator,
    ExecutionEvaluator,
    MemoryEvaluator,
    PlanEvaluator,
    ReflectionEvaluator,
)
from maple_agent.evaluation.metrics import overall_score
from maple_agent.evaluation.models import (
    AgentMetrics,
    ContextEvaluationResult,
    EvaluationCase,
    EvaluationMetrics,
    EvaluationResult,
)
from maple_agent.evaluation.models import EvaluationReport as ContextEvaluationReport
from maple_agent.game_state.models import EntityLifecycle
from maple_agent.knowledge_graph.graph import KnowledgeGraph
from maple_agent.knowledge_graph.models import (
    ItemNode,
    KnowledgeEntityProvenance,
    MapNode,
    NPCNode,
    QuestNode,
    Relation,
)
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


def load_benchmark_fixture(
    path: str | Path | None = None,
) -> tuple[KnowledgeGraph, list[EvaluationCase]]:
    """Load the sanitized Phase 13-P semantic benchmark and graph."""
    fixture_path = Path(path) if path is not None else (
        Path(__file__).parent / "phase13p_benchmark.json"
    )
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    provenance = KnowledgeEntityProvenance(
        source_id=payload["dataset_id"],
        source_type="SANITIZED_FIXTURE",
        source_reference="phase13p_benchmark",
        source_name="Phase 13-P semantic benchmark",
        game_profile=payload["profile"],
        server_profile=payload["server_profile"],
        data_version=payload["version"],
        snapshot_version=payload["version"],
        content_hash=payload["content_hash"],
        adapter_name="phase13p-fixture-adapter",
        adapter_version="1",
    )
    graph_data = payload["graph"]
    graph = KnowledgeGraph(
        maps=[
            MapNode.model_validate({**item, "provenance": provenance})
            for item in graph_data["maps"]
        ],
        npcs=[
            NPCNode.model_validate({**item, "provenance": provenance})
            for item in graph_data["npcs"]
        ],
        quests=[
            QuestNode.model_validate({**item, "provenance": provenance})
            for item in graph_data["quests"]
        ],
        items=[
            ItemNode.model_validate({**item, "provenance": provenance})
            for item in graph_data["items"]
        ],
        relations=[
            Relation.model_validate({**item, "provenance": provenance})
            for item in graph_data["relations"]
        ],
    )
    cases = [EvaluationCase.model_validate(item) for item in payload["cases"]]
    return graph, cases


def evaluate_cases(
    cases: list[EvaluationCase],
    reasoner: ContextReasoner,
    *,
    dataset_reference: str = "phase13p-context-fixture-v1",
) -> ContextEvaluationReport:
    """Compare expected semantic contexts without changing any upstream result."""
    results: list[ContextEvaluationResult] = []
    for case in cases:
        case_reasoner = reasoner
        if case.relation_confidence_threshold is not None:
            case_reasoner = ContextReasoner(
                reasoner.graph,
                relation_confidence_threshold=case.relation_confidence_threshold,
            )
        context = case_reasoner.reason(case.semantic_state, case.temporal_state)
        actual_active = context.context_type is not ContextType.UNKNOWN_CONTEXT
        actual_uncertainty = bool(context.uncertainties)
        input_min = min(case.input_confidences) if case.input_confidences else None
        violations = int(
            input_min is not None and context.confidence > input_min + 1e-9
        )
        failures: list[str] = []
        if context.context_type is not case.expected_context:
            failures.append(
                f"context expected {case.expected_context.value}, "
                f"got {context.context_type.value}"
            )
        if actual_active is not case.expected_active:
            failures.append("active-context expectation mismatch")
        if case.expected_uncertainty and not actual_uncertainty:
            failures.append("expected uncertainty was not preserved")
        if case.expects_conflict_preservation and not any(
            "conflict" in item for item in context.uncertainties
        ):
            failures.append("conflict uncertainty was not preserved")
        if case.expects_expired_exclusion and any(
            entity.lifecycle is EntityLifecycle.EXPIRED
            and not entity.historical_only
            for entity in context.related_entities
        ):
            failures.append("expired entity entered active context")
        if case.expects_historical_reference and not any(
            entity.historical_only for entity in context.related_entities
        ):
            failures.append("lost reference was not retained as historical")
        if violations:
            failures.append("context confidence exceeded weakest input confidence")
        results.append(
            ContextEvaluationResult(
                case_id=case.case_id,
                input_reference=case.input_reference,
                expected_context=case.expected_context,
                actual_context=context.context_type,
                expected_active=case.expected_active,
                actual_active=actual_active,
                expected_uncertainty=case.expected_uncertainty,
                actual_uncertainty=actual_uncertainty,
                confidence=context.confidence,
                input_min_confidence=input_min,
                confidence_bound_violations=violations,
                uncertainty=context.uncertainties,
                passed=not failures,
                failure_reason="; ".join(failures),
            )
        )
    return ContextEvaluationReport(
        report_id="phase13p-context-evaluation",
        dataset_reference=dataset_reference,
        results=results,
        metrics=_metrics(results, cases),
    )


def _metrics(
    results: list[ContextEvaluationResult],
    cases: list[EvaluationCase],
) -> EvaluationMetrics:
    """Compute metrics with denominators instead of optimistic defaults."""
    by_id = {case.case_id: case for case in cases}

    def rate(values: list[bool], name: str) -> float | None:
        if not values:
            return None
        return round(sum(values) / len(values), 4)

    context_values = [
        result.actual_context is result.expected_context for result in results
    ]
    unknown_values = [
        result.actual_context is ContextType.UNKNOWN_CONTEXT
        for result in results
        if result.expected_context is ContextType.UNKNOWN_CONTEXT
    ]
    conflict_values = [
        bool(result.uncertainty)
        for result in results
        if by_id[result.case_id].expects_conflict_preservation
    ]
    no_active_cases = [
        result for result in results if not result.expected_active
    ]
    false_promotions = [result.actual_active for result in no_active_cases]
    expired_values = [
        result.actual_context is ContextType.UNKNOWN_CONTEXT
        for result in results
        if by_id[result.case_id].expects_expired_exclusion
    ]
    lost_values = [
        any("historical" in item for item in result.uncertainty)
        for result in results
        if by_id[result.case_id].expects_historical_reference
    ]
    denominators = {
        "context_accuracy": len(context_values),
        "unknown_preservation_rate": len(unknown_values),
        "conflict_preservation_rate": len(conflict_values),
        "false_promotion_rate": len(false_promotions),
        "expired_exclusion_rate": len(expired_values),
        "lost_handling_accuracy": len(lost_values),
    }
    return EvaluationMetrics(
        denominator_status=(
            "SUFFICIENT" if results else "INSUFFICIENT_DATA"
        ),
        denominators=denominators,
        context_accuracy=rate(context_values, "context_accuracy"),
        unknown_preservation_rate=rate(unknown_values, "unknown_preservation_rate"),
        conflict_preservation_rate=rate(conflict_values, "conflict_preservation_rate"),
        false_promotion_rate=rate(false_promotions, "false_promotion_rate"),
        expired_exclusion_rate=rate(expired_values, "expired_exclusion_rate"),
        lost_handling_accuracy=rate(lost_values, "lost_handling_accuracy"),
        confidence_bound_violation_count=sum(
            result.confidence_bound_violations for result in results
        ),
    )
