"""FailurePredictor:失败概率预测 + 预防参考生成(只读)。"""

from __future__ import annotations

import json
from pathlib import Path

from maple_agent.architecture import TRACE_SCHEMA_VERSION
from maple_agent.failure_intelligence.models import (
    FailurePatternRecord,
    FailurePreventionReference,
    RootCauseAnalysis,
)
from maple_agent.task_planning.models import TaskGraph


class FailurePredictor:
    """预测任务失败概率,生成规划预防参考。"""

    def predict(
        self,
        *,
        task_graph: TaskGraph,
        patterns: list[FailurePatternRecord],
    ) -> dict[str, float]:
        task_failure: dict[str, float] = {}
        task_ids = {task.task_id for task in task_graph.tasks}
        for pattern in patterns:
            for task_id in pattern.affected_tasks:
                if task_id not in task_ids:
                    continue
                base = (
                    1 - pattern.success_rate
                    if pattern.success_rate
                    else 0.5
                )
                task_failure[task_id] = max(
                    task_failure.get(task_id, 0),
                    round(base, 4),
                )
        for task in task_graph.tasks:
            task_failure.setdefault(task.task_id, 0.1)
        return task_failure

    def build_prevention_reference(
        self,
        *,
        task_graph: TaskGraph,
        patterns: list[FailurePatternRecord],
        analysis: RootCauseAnalysis | None = None,
    ) -> FailurePreventionReference:
        task_failure = self.predict(
            task_graph=task_graph,
            patterns=patterns,
        )
        avoid: list[str] = []
        warnings: list[str] = []
        recovery: list[str] = []
        notes: list[str] = []
        for task_id, probability in sorted(task_failure.items()):
            if probability >= 0.6:
                avoid.append(task_id)
                warnings.append(
                    f"{task_id} 失败概率 {probability:.0%},建议规避或强化前置"
                )
            elif probability >= 0.3:
                recovery.append(f"recovery:{task_id}")
                warnings.append(
                    f"{task_id} 中风险,增加恢复点"
                )
        if analysis is not None:
            notes.append(f"根因: {analysis.root_cause}")
            notes.append(f"预防: {analysis.prevention_strategy}")
        for pattern in patterns:
            notes.append(
                f"历史模式 {pattern.pattern_id}: "
                f"{pattern.resolution_strategy}"
            )
        return FailurePreventionReference(
            avoid_tasks=avoid,
            risk_warnings=warnings,
            recovery_points=recovery,
            prevention_notes=notes,
            summary="; ".join(warnings + notes) or "无风险",
        )


def save_failure_intelligence_trace(
    sessions_dir: str | Path,
    trace_id: str,
    *,
    source_trace: str,
    failure_pattern,
    analysis: RootCauseAnalysis,
    prevention_reference: FailurePreventionReference,
) -> None:
    """写入 failure_intelligence_trace.json(统一 Replay)。"""
    directory = Path(sessions_dir) / trace_id
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "source_trace": source_trace,
        "failure_pattern": failure_pattern.model_dump(mode="json"),
        "analysis": analysis.model_dump(mode="json"),
        "prevention_reference": prevention_reference.model_dump(mode="json"),
    }
    (directory / "failure_intelligence_trace.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
