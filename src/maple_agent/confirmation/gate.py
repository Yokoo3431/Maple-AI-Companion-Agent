"""HumanConfirmationGate:ActionPlan + Vision + Decision -> 确认请求(只读)。"""

from __future__ import annotations

from datetime import UTC, datetime

from maple_agent.action_plan.models import ActionPlan
from maple_agent.confirmation.models import (
    ConfirmationRequest,
    ConfirmationStatus,
)
from maple_agent.decision.models import DecisionResult
from maple_agent.logging_setup import new_id
from maple_agent.vision_eval.models import VisionEvaluationResult


class HumanConfirmationGate:
    """生成人工确认请求;HIGH 风险自动阻断,低置信进入 PENDING。"""

    def __init__(self, *, min_confidence: float = 0.6) -> None:
        self.min_confidence = min_confidence

    def create_request(
        self,
        *,
        action_plan: ActionPlan,
        vision_result: VisionEvaluationResult | None = None,
        decision_result: DecisionResult | None = None,
        trace_id: str | None = None,
    ) -> ConfirmationRequest:
        risk_level = (
            vision_result.risk_level.value
            if vision_result is not None
            else "LOW"
        )
        vision_score = (
            vision_result.overall_score
            if vision_result is not None
            else 0.0
        )
        confidence = (
            decision_result.selected_option.confidence
            if decision_result is not None
            and decision_result.selected_option is not None
            else 0.0
        )
        status = ConfirmationStatus.PENDING
        reason = "等待人工确认"
        if risk_level == "HIGH":
            status = ConfirmationStatus.BLOCKED
            reason = "视觉风险评估为 HIGH,自动阻断"
        elif confidence < self.min_confidence:
            reason = (
                f"置信度 {confidence:.2f} 低于阈值 "
                f"{self.min_confidence:.2f},需人工确认"
            )
        return ConfirmationRequest(
            confirmation_id=new_id(),
            trace_id=trace_id or "",
            action_plan_id=action_plan.plan_id,
            action=action_plan.action,
            target=action_plan.target,
            risk_level=risk_level,
            vision_score=round(vision_score, 4),
            confidence=round(confidence, 4),
            reason=reason,
            created_at=datetime.now(UTC),
            status=status,
        )
