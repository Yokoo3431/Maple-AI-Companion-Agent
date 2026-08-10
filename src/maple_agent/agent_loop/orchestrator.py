"""AgentLoopOrchestrator:统一认知循环编排(只读,Mock Only)。"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from maple_agent.action_plan.models import ActionPlanStatus
from maple_agent.action_plan.planner import ActionPlanner
from maple_agent.agent_loop.models import AgentLoopContext, AgentLoopStatus
from maple_agent.agent_loop.trace import (
    AgentLoopStage,
    AgentLoopTrace,
    AgentLoopTraceWriter,
)
from maple_agent.agent_loop.validator import (
    AgentLoopValidationResult,
    AgentLoopValidator,
)
from maple_agent.confirmation.gate import HumanConfirmationGate
from maple_agent.confirmation.manager import ConfirmationManager
from maple_agent.confirmation.models import ConfirmationStatus
from maple_agent.context.models import KnowledgeState, MatchedEntity
from maple_agent.decision.engine import DecisionEngine
from maple_agent.decision.models import DecisionContext, DecisionOption
from maple_agent.evaluation.benchmark import EvaluationBenchmark
from maple_agent.evaluation.models import EvaluationResult
from maple_agent.execution.feedback import ExecutionFeedback
from maple_agent.executor.models import ExecutionResult, ExecutionStatus
from maple_agent.executor_sandbox.models import (
    SandboxExecutionRequest,
    SandboxExecutionStatus,
)
from maple_agent.executor_sandbox.sandbox import LimitedExecutorSandbox
from maple_agent.fusion.models import WorldState
from maple_agent.goal.models import Goal
from maple_agent.logging_setup import TraceContext, new_id
from maple_agent.observation.collector import ObservationCollector
from maple_agent.observation.models import ObservationState
from maple_agent.providers.knowledge import KnowledgeProvider
from maple_agent.reflection.engine import ReflectionEngine
from maple_agent.vision_eval.evaluator import VisionEvaluator
from maple_agent.vision_eval.models import RiskLevel

logger = logging.getLogger("maple_agent.agent_loop")


class AgentLoopOrchestrator:
    """串联 Observation -> Evaluation -> Decision -> Plan -> Confirmation
    -> Sandbox -> Reflection -> Benchmark;全部只读。"""

    def __init__(
        self,
        *,
        observation_collector: ObservationCollector,
        vision_evaluator: VisionEvaluator,
        decision_engine: DecisionEngine,
        action_planner: ActionPlanner,
        confirmation_manager: ConfirmationManager,
        confirmation_gate: HumanConfirmationGate,
        sandbox: LimitedExecutorSandbox,
        reflection_engine: ReflectionEngine,
        evaluation_benchmark: EvaluationBenchmark,
        sessions_dir: str | Path = "sessions",
        knowledge: KnowledgeProvider | None = None,
        option_builder: Callable[[ObservationState, Goal | None], list[DecisionOption]]
        | None = None,
    ) -> None:
        self.observation_collector = observation_collector
        self.vision_evaluator = vision_evaluator
        self.decision_engine = decision_engine
        self.action_planner = action_planner
        self.confirmation_manager = confirmation_manager
        self.confirmation_gate = confirmation_gate
        self.sandbox = sandbox
        self.reflection_engine = reflection_engine
        self.evaluation_benchmark = evaluation_benchmark
        self.sessions_dir = Path(sessions_dir)
        self.knowledge = knowledge
        self.option_builder = option_builder or self._default_options
        self.trace_writer = AgentLoopTraceWriter(sessions_dir)
        self.validator = AgentLoopValidator()
        self.context: AgentLoopContext | None = None
        self.last_trace: AgentLoopTrace | None = None
        self.last_validation: AgentLoopValidationResult | None = None

    def run(
        self,
        *,
        image_path: str | Path | None = None,
        image_bytes: bytes | None = None,
        goal: Goal | None = None,
        auto_approve: bool = True,
        trace_id: str | None = None,
    ) -> AgentLoopContext:
        """执行完整认知循环(仅 Mock,无真实执行)。"""
        with TraceContext(trace_id=trace_id) as trace:
            tid = trace.trace_id
            stages: list[AgentLoopStage] = []
            context = AgentLoopContext(
                trace_id=tid,
                status=AgentLoopStatus.CREATED,
            )
            try:
                context = self._run_stages(
                    context,
                    stages,
                    tid,
                    image_path=image_path,
                    image_bytes=image_bytes,
                    goal=goal,
                    auto_approve=auto_approve,
                )
            except Exception as exc:
                context = context.model_copy(
                    update={"status": AgentLoopStatus.FAILED}
                )
                stages.append(
                    AgentLoopStage(stage="error", status=str(exc))
                )
                logger.error("agent loop failed: %s", exc)
            trace_data = AgentLoopTrace(
                trace_id=tid,
                stages=stages,
                final_status=context.status.value,
            )
            self.trace_writer.write(trace_data)
            self.last_trace = trace_data
            self.context = context
            self.last_validation = self.validator.validate(context, trace_data)
            logger.info(
                "agent loop: trace=%s final=%s stages=%d",
                tid,
                context.status.value,
                len(stages),
            )
            return context

    def _run_stages(
        self,
        context: AgentLoopContext,
        stages: list[AgentLoopStage],
        tid: str,
        *,
        image_path: str | Path | None,
        image_bytes: bytes | None,
        goal: Goal | None,
        auto_approve: bool,
    ) -> AgentLoopContext:
        # 1. Observation
        context = context.model_copy(
            update={"status": AgentLoopStatus.OBSERVING}
        )
        observation_state = self.observation_collector.collect_and_save(
            image_path=image_path,
            image_bytes=image_bytes,
            source="agent_loop",
            trace_id=tid,
        )
        context = context.model_copy(
            update={"observation_state": observation_state}
        )
        stages.append(AgentLoopStage(stage="observation", status="completed"))

        # 2. Vision Evaluation
        context = context.model_copy(
            update={"status": AgentLoopStatus.EVALUATING}
        )
        vision_result = self.vision_evaluator.evaluate(
            frame=self.observation_collector.last_frame,
            state=observation_state,
            trace_id=tid,
        )
        context = context.model_copy(update={"vision_result": vision_result})
        stages.append(
            AgentLoopStage(
                stage="vision_evaluation",
                status=vision_result.risk_level.value,
            )
        )
        if vision_result.risk_level is RiskLevel.HIGH:
            return context.model_copy(
                update={"status": AgentLoopStatus.BLOCKED}
            )

        # 3. Knowledge + Decision
        context = context.model_copy(
            update={"status": AgentLoopStatus.DECIDING}
        )
        world_state = self._build_world_state(observation_state, tid)
        knowledge_state = self._build_knowledge_state(
            observation_state,
            tid,
        )
        options = self.option_builder(observation_state, goal)
        decision_result = self.decision_engine.decide(
            DecisionContext(
                world_state=world_state,
                knowledge_state=knowledge_state,
                goal=goal,
                options=options,
            ),
            trace_id=tid,
        )
        if decision_result.selected_option is None:
            return context.model_copy(
                update={"status": AgentLoopStatus.BLOCKED}
            )
        context = context.model_copy(
            update={"decision_result": decision_result}
        )
        stages.append(AgentLoopStage(stage="decision", status="completed"))

        # 4. Action Plan
        context = context.model_copy(
            update={"status": AgentLoopStatus.PLANNING}
        )
        action_plan = self.action_planner.plan(
            decision_result,
            world_state=world_state,
            knowledge_state=knowledge_state,
            goal_id=goal.goal_id if goal is not None else None,
            trace_id=tid,
        )
        if action_plan.status is ActionPlanStatus.BLOCKED:
            return context.model_copy(
                update={"status": AgentLoopStatus.BLOCKED}
            )
        context = context.model_copy(update={"action_plan": action_plan})
        stages.append(AgentLoopStage(stage="planning", status="completed"))

        # 5. Human Confirmation
        context = context.model_copy(
            update={"status": AgentLoopStatus.WAITING_CONFIRMATION}
        )
        confirmation = self.confirmation_gate.create_request(
            action_plan=action_plan,
            vision_result=vision_result,
            decision_result=decision_result,
            trace_id=tid,
        )
        self.confirmation_manager.create(confirmation)
        context = context.model_copy(
            update={"confirmation_result": confirmation}
        )
        stages.append(
            AgentLoopStage(
                stage="confirmation",
                status=confirmation.status.value,
            )
        )
        if confirmation.status is ConfirmationStatus.BLOCKED:
            return context.model_copy(
                update={"status": AgentLoopStatus.BLOCKED}
            )

        # 6. 等待人工状态(模拟批准)
        token = None
        if auto_approve:
            token = self.confirmation_manager.approve(
                confirmation.confirmation_id
            )
            context = context.model_copy(
                update={"status": AgentLoopStatus.AUTHORIZED}
            )
        if token is None:
            return context.model_copy(
                update={"status": AgentLoopStatus.BLOCKED}
            )
        context = context.model_copy(update={"permission_token": token})

        # 7. Sandbox(Mock)
        context = context.model_copy(
            update={"status": AgentLoopStatus.SANDBOX_EXECUTING}
        )
        sandbox_request = SandboxExecutionRequest(
            execution_id=new_id(),
            trace_id=tid,
            permission_token_id=token.token_id,
            action=action_plan.action,
            target=action_plan.target,
            scope=token.scope,
        )
        sandbox_result = self.sandbox.execute(
            request=sandbox_request,
            token=token,
            trace_id=tid,
        )
        if sandbox_result.status is not SandboxExecutionStatus.COMPLETED:
            return context.model_copy(
                update={"status": AgentLoopStatus.BLOCKED}
            )
        context = context.model_copy(
            update={"sandbox_result": sandbox_result}
        )
        stages.append(
            AgentLoopStage(
                stage="sandbox",
                status=sandbox_result.mode,
            )
        )

        # 8. Reflection
        context = context.model_copy(
            update={"status": AgentLoopStatus.REFLECTING}
        )
        execution = ExecutionResult(
            execution_id=sandbox_request.execution_id,
            status=ExecutionStatus.COMPLETED,
            message=sandbox_result.message,
            trace_id=tid,
        )
        feedback = ExecutionFeedback(
            execution_id=sandbox_request.execution_id,
            observed={"sandbox_ok": True},
            success=True,
            reason="mock observation",
            trace_id=tid,
        )
        reflection_result = self.reflection_engine.reflect(
            execution,
            feedback=feedback,
            expected_result=action_plan.expected_result,
            trace_id=tid,
        )
        context = context.model_copy(
            update={"reflection_result": reflection_result}
        )
        stages.append(
            AgentLoopStage(stage="reflection", status="completed")
        )

        # 9. Evaluation Benchmark
        evaluation_result: EvaluationResult = self.evaluation_benchmark.run(tid)
        context = context.model_copy(
            update={"evaluation_result": evaluation_result}
        )
        stages.append(AgentLoopStage(stage="evaluation", status="completed"))

        return context.model_copy(
            update={"status": AgentLoopStatus.COMPLETED}
        )

    def _build_knowledge_state(
        self,
        observation_state: ObservationState,
        tid: str,
    ) -> KnowledgeState | None:
        if self.knowledge is None:
            return None
        map_name = observation_state.map_name
        map_info = (
            self.knowledge.get_map(map_name, trace_id=tid) if map_name else None
        )
        entities: list[MatchedEntity] = []
        if map_info is not None:
            entities.append(
                MatchedEntity(
                    entity_type="map",
                    entity_id=map_info.map_id,
                    name=map_info.name,
                    confidence=observation_state.confidence,
                )
            )
        return KnowledgeState(
            matched_entities=entities,
            top_candidates=entities,
            confidence=observation_state.confidence,
            source="agent_loop",
            selection_reason=f"best={map_name}" if map_name else "",
        )

    def _build_world_state(
        self,
        observation_state: ObservationState,
        tid: str,
    ) -> WorldState | None:
        if self.knowledge is None or not observation_state.map_name:
            return None
        map_info = self.knowledge.get_map(
            observation_state.map_name,
            trace_id=tid,
        )
        return WorldState(
            current_map=map_info,
            confidence=observation_state.confidence,
            trace_id=tid,
        )

    @staticmethod
    def _default_options(
        observation_state: ObservationState,
        goal: Goal | None,
    ) -> list[DecisionOption]:
        options = [
            DecisionOption(
                decision_id="opt-observe",
                action="OBSERVE",
                target="window",
                confidence=observation_state.confidence,
                risk=0.1,
                reason="观察当前窗口状态",
            ),
            DecisionOption(
                decision_id="opt-query",
                action="QUERY_KNOWLEDGE",
                target=observation_state.map_name or "map",
                confidence=observation_state.confidence,
                risk=0.1,
                reason="查询知识库确认位置",
            ),
        ]
        for index, entity in enumerate(observation_state.visible_entities):
            options.append(
                DecisionOption(
                    decision_id=f"opt-talk-{index}",
                    action="TALK",
                    target=entity,
                    confidence=observation_state.confidence,
                    risk=0.2,
                    reason=f"与可见实体 {entity} 对话",
                )
            )
        return options
