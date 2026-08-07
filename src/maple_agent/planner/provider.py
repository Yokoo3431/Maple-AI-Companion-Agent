"""PlannerProvider 契约与 Mock(Phase 1.7,不调用 LLM)。"""

from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable

from maple_agent.logging_setup import TraceContext, new_id
from maple_agent.planner.models import PlannerInput, PlanResult, PlanStep

logger = logging.getLogger("maple_agent.planner")


@runtime_checkable
class PlannerProvider(Protocol):
    """Planner 契约:仅定义 plan(context)。"""

    def plan(self, context: PlannerInput) -> PlanResult: ...


class MockPlannerProvider:
    """Mock 实现:固定计划;可配置失败。"""

    def __init__(
        self,
        *,
        steps: list[PlanStep] | None = None,
        raise_on_plan: bool = False,
    ) -> None:
        self._steps = steps or [
            PlanStep(
                step_id="step-1",
                action="observe",
                target="window",
                expected_outcome="screen frame",
            ),
            PlanStep(
                step_id="step-2",
                action="report",
                target="context",
                expected_outcome="agent context",
            ),
        ]
        self._raise_on_plan = raise_on_plan
        self.call_count = 0

    def plan(self, context: PlannerInput) -> PlanResult:
        self.call_count += 1
        if self._raise_on_plan:
            raise RuntimeError("mock planner failure")
        with TraceContext(trace_id=context.trace_id):
            result = PlanResult(
                plan_id=new_id(),
                goal_id=context.goals[0].goal_id if context.goals else "",
                steps=self._steps,
                summary=f"plan for {context.context.runtime_state}",
                confidence=0.9,
                trace_id=context.trace_id,
            )
            logger.info(
                "planner plan: goal=%s steps=%d",
                result.goal_id,
                len(result.steps),
            )
            return result
