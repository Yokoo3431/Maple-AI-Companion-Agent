"""AdaptivePlannerOptimizer:经验引导的自适应规划优化(只读)。"""

from __future__ import annotations

import json
from pathlib import Path

from maple_agent.architecture import TRACE_SCHEMA_VERSION
from maple_agent.goal_memory.models import GoalExperienceRecord
from maple_agent.planning_optimizer.analyzer import TaskGraphAnalyzer
from maple_agent.planning_optimizer.models import (
    OptimizedPlanningReference,
    PlanningAnalysis,
    PlanningQualityScore,
)
from maple_agent.planning_optimizer.scorer import PlanningScorer
from maple_agent.task_planning.models import TaskGraph


class AdaptivePlannerOptimizer:
    """分析当前任务图,引入历史经验,输出优化规划参考。"""

    def __init__(
        self,
        *,
        analyzer: TaskGraphAnalyzer | None = None,
        scorer: PlanningScorer | None = None,
    ) -> None:
        self.analyzer = analyzer or TaskGraphAnalyzer()
        self.scorer = scorer or PlanningScorer()
        self.last_analysis: PlanningAnalysis | None = None
        self.last_score: PlanningQualityScore | None = None
        self.last_reference: OptimizedPlanningReference | None = None

    def optimize(
        self,
        *,
        graph: TaskGraph,
        experience: GoalExperienceRecord | None = None,
        analysis: PlanningAnalysis | None = None,
    ) -> tuple[OptimizedPlanningReference, PlanningQualityScore]:
        analysis = analysis or self.analyzer.analyze(graph)
        removed = list(analysis.redundant_tasks)
        tasks = [
            task
            for task in graph.tasks
            if task.task_id not in set(removed)
        ]
        reasoning: list[str] = []
        if experience is not None:
            failed = set(experience.failed_points)
            for task in list(tasks):
                if task.task_id in failed:
                    tasks.remove(task)
                    removed.append(task.task_id)
            if experience.successful_path:
                order = {
                    task_id: index
                    for index, task_id in enumerate(
                        experience.successful_path
                    )
                }
                tasks.sort(
                    key=lambda task: order.get(task.task_id, len(order))
                )
                reasoning.append("按历史成功路径重排任务")
            if experience.success:
                reasoning.append("历史目标成功,沿用其策略")
        risk_nodes = set(analysis.risk_nodes)
        added_recovery = [
            f"recovery:{task_id}" for task_id in sorted(risk_nodes)
        ]
        risk_adjustments = [
            f"{task_id} 风险调整: 增加恢复点"
            for task_id in sorted(risk_nodes)
        ]
        if risk_nodes:
            reasoning.append("高风险节点增加恢复点")
        if removed:
            reasoning.append("移除冗余/失败任务: " + ", ".join(removed))
        optimized_order = [task.task_id for task in tasks]
        reference = OptimizedPlanningReference(
            goal_id=graph.goal_id,
            optimized_order=optimized_order,
            removed_tasks=removed,
            added_recovery_points=added_recovery,
            risk_adjustments=risk_adjustments,
            reasoning=reasoning,
            summary="; ".join(reasoning) or "无优化",
        )
        experience_match = self._experience_match(graph, experience)
        analysis = analysis.model_copy(
            update={"experience_match": experience_match}
        )
        score = self.scorer.score(
            analysis=analysis,
            experience=experience,
            optimized=reference,
        )
        self.last_analysis = analysis
        self.last_score = score
        self.last_reference = reference
        return reference, score

    @staticmethod
    def _experience_match(
        graph: TaskGraph,
        experience: GoalExperienceRecord | None,
    ) -> float:
        if experience is None:
            return 0.0
        task_ids = {task.task_id for task in graph.tasks}
        if not task_ids:
            return 0.0
        overlap = len(task_ids & set(experience.task_pattern))
        return round(overlap / len(task_ids), 4)


def save_planning_optimization_trace(
    sessions_dir: str | Path,
    trace_id: str,
    *,
    goal_id: str,
    original_plan: dict,
    analysis: PlanningAnalysis,
    optimized_plan: OptimizedPlanningReference,
    score: PlanningQualityScore,
) -> None:
    """写入 planning_optimization_trace.json(统一 Replay)。"""
    directory = Path(sessions_dir) / trace_id
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "goal_id": goal_id,
        "original_plan": original_plan,
        "analysis": analysis.model_dump(mode="json"),
        "optimized_plan": optimized_plan.model_dump(mode="json"),
        "score": score.planning_score,
        "recommendations": score.recommendations,
    }
    (directory / "planning_optimization_trace.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
