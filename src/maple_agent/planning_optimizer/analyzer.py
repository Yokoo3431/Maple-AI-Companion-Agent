"""TaskGraphAnalyzer:分析任务图完整性/冗余/风险/失败概率(只读)。"""

from __future__ import annotations

from maple_agent.planning_optimizer.models import PlanningAnalysis
from maple_agent.task_planning.models import TaskGraph
from maple_agent.task_planning.validator import LongHorizonValidator


class TaskGraphAnalyzer:
    """评估任务图质量,识别风险与冗余。"""

    def analyze(self, graph: TaskGraph) -> PlanningAnalysis:
        issues: list[str] = []
        task_ids = [task.task_id for task in graph.tasks]
        if not task_ids:
            issues.append("任务图为空")
        validation = LongHorizonValidator().validate(graph)
        has_cycle = any(
            "循环依赖" in issue for issue in validation.issues
        )
        dag_complete = bool(task_ids) and not has_cycle
        if has_cycle:
            issues.append("任务图存在循环依赖")
        redundant: list[str] = []
        if len(task_ids) > 8:
            redundant = task_ids[8:]
            issues.append("任务冗余: 超过 8 个节点")
        risk_nodes = [
            task.task_id
            for task in graph.tasks
            if task.failure_condition and "失败" in task.failure_condition
        ]
        risk_ratio = len(risk_nodes) / max(1, len(task_ids))
        failure_probability = round(
            min(
                1.0,
                0.2 + 0.3 * risk_ratio + (0.2 if not dag_complete else 0.0),
            ),
            4,
        )
        return PlanningAnalysis(
            goal_id=graph.goal_id,
            dag_complete=dag_complete,
            redundant_tasks=redundant,
            risk_nodes=risk_nodes,
            failure_probability=failure_probability,
            task_count=len(task_ids),
            issues=issues,
        )
