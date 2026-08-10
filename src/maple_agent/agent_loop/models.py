"""Agent Cognitive Loop 数据模型(Phase 6-E,统一闭环编排,只读)。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel

from maple_agent.action_plan.models import ActionPlan
from maple_agent.confirmation.models import (
    ConfirmationRequest,
    PermissionToken,
)
from maple_agent.decision.models import DecisionResult
from maple_agent.evaluation.models import EvaluationResult
from maple_agent.executor_sandbox.models import SandboxExecutionResult
from maple_agent.observation.models import ObservationState
from maple_agent.reflection.models import ReflectionResult
from maple_agent.vision_eval.models import VisionEvaluationResult


class AgentLoopStatus(StrEnum):
    """认知循环状态。"""

    CREATED = "CREATED"
    OBSERVING = "OBSERVING"
    EVALUATING = "EVALUATING"
    DECIDING = "DECIDING"
    PLANNING = "PLANNING"
    WAITING_CONFIRMATION = "WAITING_CONFIRMATION"
    AUTHORIZED = "AUTHORIZED"
    SANDBOX_EXECUTING = "SANDBOX_EXECUTING"
    REFLECTING = "REFLECTING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    BLOCKED = "BLOCKED"


class AgentLoopContext(BaseModel):
    """完整认知循环上下文(各阶段产物)。"""

    trace_id: str = ""
    observation_state: ObservationState | None = None
    vision_result: VisionEvaluationResult | None = None
    decision_result: DecisionResult | None = None
    action_plan: ActionPlan | None = None
    confirmation_result: ConfirmationRequest | None = None
    permission_token: PermissionToken | None = None
    sandbox_result: SandboxExecutionResult | None = None
    reflection_result: ReflectionResult | None = None
    evaluation_result: EvaluationResult | None = None
    status: AgentLoopStatus = AgentLoopStatus.CREATED
