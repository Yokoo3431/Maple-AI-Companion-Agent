"""FailureExtractor:Reflection + Trace -> FailurePatternRecord(只读)。"""

from __future__ import annotations

from maple_agent.failure_intelligence.models import FailurePatternRecord
from maple_agent.logging_setup import new_id
from maple_agent.reflection.models import ReflectionResult


class FailureExtractor:
    """从失败反思与执行/规划 Trace 提取结构化失败模式。"""

    _RESOLUTIONS = {
        "EXECUTION_FAILED": "重试并检查前置条件",
        "WORLD_MISMATCH": "重新观察世界状态",
        "KNOWLEDGE_ERROR": "刷新知识库",
        "LOW_CONFIDENCE": "请求人工确认",
        "OBSERVATION_FAILED": "重新采集观察",
    }

    def extract(
        self,
        *,
        reflection: ReflectionResult,
        execution_trace: dict | None = None,
        task_planning_trace: dict | None = None,
    ) -> FailurePatternRecord | None:
        """仅对失败反思提取模式;成功反思返回 None。"""
        if reflection.success:
            return None
        failure_type = (
            reflection.failure_type.value
            if reflection.failure_type is not None
            else "UNKNOWN"
        )
        affected_tasks = self._affected_tasks(
            execution_trace,
            task_planning_trace,
        )
        return FailurePatternRecord(
            pattern_id=new_id(),
            failure_type=failure_type,
            trigger_conditions=self._trigger_conditions(
                reflection,
                task_planning_trace,
            ),
            context_snapshot={
                "confidence": reflection.confidence,
                "next_action": reflection.next_action,
                "failed_task": affected_tasks[0] if affected_tasks else "",
            },
            affected_tasks=affected_tasks,
            root_cause=reflection.failure_reason or f"{failure_type} 导致失败",
            resolution_strategy=self._RESOLUTIONS.get(
                failure_type,
                "重新规划",
            ),
            success_rate=0.0,
            confidence=reflection.confidence,
            trace_id=reflection.trace_id,
        )

    @staticmethod
    def _affected_tasks(
        execution_trace: dict | None,
        task_planning_trace: dict | None,
    ) -> list[str]:
        tasks: list[str] = []
        if execution_trace:
            for step in execution_trace.get("steps", []):
                if step.get("status") in ("FAILED", "BLOCKED"):
                    task = (
                        step.get("task", {}).get("step_id")
                        or step.get("step_id")
                    )
                    if task:
                        tasks.append(str(task))
        if not tasks and task_planning_trace:
            current = task_planning_trace.get("current_task")
            if current:
                tasks.append(str(current))
        return tasks

    @staticmethod
    def _trigger_conditions(
        reflection: ReflectionResult,
        task_planning_trace: dict | None,
    ) -> list[str]:
        conditions = [f"confidence={reflection.confidence:.2f}"]
        if task_planning_trace:
            progress = task_planning_trace.get("progress")
            if progress is not None:
                conditions.append(f"progress={progress}")
        return conditions
