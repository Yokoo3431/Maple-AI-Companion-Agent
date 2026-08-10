"""ReflectionEngine:ExecutionResult + Feedback + WorldState → ReflectionResult。"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from maple_agent.execution.feedback import ExecutionFeedback
from maple_agent.executor.models import ExecutionResult, ExecutionStatus
from maple_agent.fusion.models import WorldState
from maple_agent.logging_setup import TraceContext, new_id
from maple_agent.reflection.memory import ReflectionMemory
from maple_agent.reflection.models import FailureType, ReflectionResult
from maple_agent.reflection.trigger import ReflectionTrigger, TriggerDecision

logger = logging.getLogger("maple_agent.reflection")


class ReflectionEngine:
    """分析执行结果与观察反馈,输出反思结论(只读)。"""

    def __init__(
        self,
        *,
        memory: ReflectionMemory | None = None,
        trigger: ReflectionTrigger | None = None,
        sessions_dir: str | Path = "sessions",
        min_confidence: float = 0.6,
    ) -> None:
        self.memory = memory or ReflectionMemory()
        self.trigger = trigger or ReflectionTrigger()
        self.sessions_dir = Path(sessions_dir)
        self.min_confidence = min_confidence
        self.last_result: ReflectionResult | None = None

    def reflect(
        self,
        execution: ExecutionResult,
        *,
        feedback: ExecutionFeedback | None = None,
        world_state: WorldState | None = None,
        expected_result: str = "",
        trace_id: str | None = None,
    ) -> ReflectionResult:
        """输入执行结果/反馈/世界状态,输出反思结果(仅分析,不执行)。"""
        with TraceContext(trace_id=trace_id) as trace:
            success, failure_type, failure_reason = self._analyze(
                execution,
                feedback=feedback,
                world_state=world_state,
            )
            confidence = self._confidence(
                execution,
                feedback=feedback,
                world_state=world_state,
            )
            result = ReflectionResult(
                reflection_id=new_id(),
                execution_id=execution.execution_id,
                expected_result=expected_result,
                actual_result=execution.message,
                success=success,
                failure_type=failure_type,
                failure_reason=failure_reason,
                confidence=round(confidence, 4),
                next_action="continue" if success else "replan",
                state_update="accepted" if success else "rejected",
                trace_id=trace.trace_id,
            )
            self.last_result = result
            self.memory.record(result)
            trigger_decision = self.trigger.evaluate(result)
            self._write_replay(
                trace.trace_id,
                execution,
                expected_result,
                result,
                trigger_decision,
            )
            logger.info(
                "reflection: success=%s failure_type=%s next=%s",
                result.success,
                result.failure_type.value if result.failure_type else None,
                result.next_action,
            )
            return result

    def _analyze(
        self,
        execution: ExecutionResult,
        *,
        feedback: ExecutionFeedback | None,
        world_state: WorldState | None,
    ) -> tuple[bool, FailureType | None, str]:
        if execution.status in (
            ExecutionStatus.FAILED,
            ExecutionStatus.BLOCKED,
        ):
            return (
                False,
                FailureType.EXECUTION_FAILED,
                execution.message or "执行失败",
            )
        observed = feedback.observed if feedback is not None else {}
        if observed.get("world_mismatch") is True:
            return (
                False,
                FailureType.WORLD_MISMATCH,
                "世界状态与预期不一致",
            )
        if observed.get("knowledge_error") is True:
            return (
                False,
                FailureType.KNOWLEDGE_ERROR,
                "知识匹配错误",
            )
        confidence = self._confidence(
            execution,
            feedback=feedback,
            world_state=world_state,
        )
        if confidence < self.min_confidence:
            return (
                False,
                FailureType.LOW_CONFIDENCE,
                f"置信度过低: {confidence:.2f} < {self.min_confidence:.2f}",
            )
        if feedback is not None and not feedback.success:
            return (
                False,
                FailureType.OBSERVATION_FAILED,
                feedback.reason or "观察反馈失败",
            )
        return True, None, ""

    @staticmethod
    def _confidence(
        execution: ExecutionResult,
        *,
        feedback: ExecutionFeedback | None,
        world_state: WorldState | None,
    ) -> float:
        if world_state is not None:
            return world_state.confidence
        if execution.status is ExecutionStatus.COMPLETED:
            return 1.0 if feedback is None or feedback.success else 0.4
        return 0.0

    def _write_replay(
        self,
        trace_id: str,
        execution: ExecutionResult,
        expected_result: str,
        result: ReflectionResult,
        trigger_decision: TriggerDecision,
    ) -> None:
        directory = self.sessions_dir / trace_id
        directory.mkdir(parents=True, exist_ok=True)
        payload = {
            "trace_id": trace_id,
            "execution": execution.model_dump(mode="json"),
            "expected": expected_result,
            "actual": result.actual_result,
            "analysis": {
                "success": result.success,
                "failure_type": (
                    result.failure_type.value
                    if result.failure_type is not None
                    else None
                ),
                "failure_reason": result.failure_reason,
                "confidence": result.confidence,
            },
            "trigger": trigger_decision.value,
            "next_plan": result.next_action,
            "reflection": result.model_dump(mode="json"),
        }
        (directory / "reflection_trace.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
