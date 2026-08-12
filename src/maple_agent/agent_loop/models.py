"""Agent Cognitive Loop 数据模型(Phase 6-E,统一闭环编排,只读)。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from maple_agent.action_plan.models import ActionPlan
from maple_agent.confirmation.models import (
    ConfirmationRequest,
    PermissionToken,
)
from maple_agent.decision.models import DecisionResult
from maple_agent.decision_reference.models import DecisionReference
from maple_agent.environment.models import (
    EnvironmentSnapshot,
    EnvironmentState,
)
from maple_agent.environment_planning.models import (
    EnvironmentPlanningReference,
)
from maple_agent.environment_reasoning.models import (
    EnvironmentInterpretation,
    EnvironmentRiskReference,
    OpportunityReference,
)
from maple_agent.evaluation.models import EvaluationResult
from maple_agent.executor_sandbox.models import SandboxExecutionResult
from maple_agent.failure_intelligence.models import (
    FailurePatternRecord,
    FailurePreventionReference,
)
from maple_agent.game_state.models import GameStateReference
from maple_agent.goal_memory.models import (
    GoalExperienceRecord,
    OptimizedTaskGraph,
)
from maple_agent.goal_scheduler.models import (
    GoalPriorityResult,
    OptimizedGoalSchedule,
)
from maple_agent.human_alignment.models import HumanAlignedDecisionReference
from maple_agent.maple_context.models import MapleCompanionContextReference
from maple_agent.maple_knowledge.models import MapleKnowledgeReference
from maple_agent.memory_association.models import SemanticMemoryReference
from maple_agent.memory_graph.models import RelevantMemoryReference
from maple_agent.observation.models import ObservationState
from maple_agent.perception.models import MaplePerceptionReference
from maple_agent.perception_fusion.models import PerceptionFusionReference
from maple_agent.planning_optimizer.models import (
    OptimizedPlanningReference,
    PlanningQualityScore,
)
from maple_agent.quest_reasoning.models import QuestGoalReference
from maple_agent.reflection.models import ReflectionResult
from maple_agent.reflex.models import ReflexReference
from maple_agent.spatial_world.models import SpatialWorldReference
from maple_agent.task_planning.models import (
    LongHorizonGoal,
    TaskExecutionState,
    TaskGraph,
)
from maple_agent.vision_eval.models import VisionEvaluationResult
from maple_agent.vision_runtime.models import ScreenObservation
from maple_agent.world_knowledge.models import WorldKnowledgeReference
from maple_agent.world_model.models import (
    EnvironmentHistory,
    EnvironmentTransition,
    PredictedEnvironmentState,
)


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
    goal_state: LongHorizonGoal | None = None
    task_graph: TaskGraph | None = None
    planning_state: TaskExecutionState | None = None
    goal_experience: GoalExperienceRecord | None = None
    planning_reference: OptimizedTaskGraph | None = None
    planning_quality: PlanningQualityScore | None = None
    optimization_reference: OptimizedPlanningReference | None = None
    failure_patterns: list[FailurePatternRecord] = Field(
        default_factory=list
    )
    failure_prevention_reference: FailurePreventionReference | None = None
    goal_schedule: OptimizedGoalSchedule | None = None
    priority_reference: list[GoalPriorityResult] = Field(
        default_factory=list
    )
    environment_state: EnvironmentState | None = None
    environment_snapshot: EnvironmentSnapshot | None = None
    environment_history: EnvironmentHistory | None = None
    world_transition: EnvironmentTransition | None = None
    environment_prediction: PredictedEnvironmentState | None = None
    environment_interpretation: EnvironmentInterpretation | None = None
    environment_opportunities: list[OpportunityReference] = Field(
        default_factory=list
    )
    environment_risk_reference: EnvironmentRiskReference | None = None
    environment_planning_reference: EnvironmentPlanningReference | None = None
    decision_reference: DecisionReference | None = None
    human_alignment_reference: HumanAlignedDecisionReference | None = None
    memory_reference: RelevantMemoryReference | None = None
    semantic_memory_reference: SemanticMemoryReference | None = None
    maple_context_reference: MapleCompanionContextReference | None = None
    maple_knowledge_reference: MapleKnowledgeReference | None = None
    perception_reference: MaplePerceptionReference | None = None
    quest_goal_reference: QuestGoalReference | None = None
    perception_fusion_reference: PerceptionFusionReference | None = None
    reflex_reference: ReflexReference | None = None
    vision_reference: ScreenObservation | None = None
    game_state_reference: GameStateReference | None = None
    world_knowledge_reference: WorldKnowledgeReference | None = None
    spatial_world_reference: SpatialWorldReference | None = None
    status: AgentLoopStatus = AgentLoopStatus.CREATED
