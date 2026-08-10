"""EvaluationReport:生成 Markdown 评估报告。"""

from __future__ import annotations

import json

from maple_agent.evaluation.models import AgentMetrics, EvaluationResult


class EvaluationReport:
    """把评估结果渲染为人类可读报告。"""

    def generate(
        self,
        result: EvaluationResult,
        metrics: AgentMetrics | None = None,
    ) -> str:
        lines = ["# Phase 5-F Evaluation Report", ""]
        if metrics is not None:
            lines.append("## Agent Metrics")
            lines.append("")
            lines.append(
                json.dumps(metrics.model_dump(), ensure_ascii=False, indent=2)
            )
            lines.append("")
        lines.append("## Trace Evaluation")
        lines.append("")
        lines.append(f"- trace_id: `{result.trace_id}`")
        lines.append(f"- decision_score: {result.decision_score:.4f}")
        lines.append(f"- planning_score: {result.planning_score:.4f}")
        lines.append(f"- execution_score: {result.execution_score:.4f}")
        lines.append(f"- reflection_score: {result.reflection_score:.4f}")
        lines.append(f"- memory_score: {result.memory_score:.4f}")
        lines.append(f"- overall_score: {result.overall_score:.4f}")
        lines.append("")
        lines.append("## Issues")
        lines.append("")
        if result.issues:
            for issue in result.issues:
                lines.append(f"- {issue}")
        else:
            lines.append("无")
        lines.append("")
        lines.append("## Recommendations")
        lines.append("")
        if result.recommendations:
            for item in result.recommendations:
                lines.append(f"- {item}")
        else:
            lines.append("无")
        return "\n".join(lines)
