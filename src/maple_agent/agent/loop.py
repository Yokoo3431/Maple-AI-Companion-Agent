"""Agent Loop 状态机与编排(Phase 1.8-B,只读;无 Executor / Input)。"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from maple_agent.context.builder import ContextBuilder
from maple_agent.context.models import (
    AgentContext,
    ExecutionContext,
    GoalContext,
    QuestPlanContext,
)
from maple_agent.events import Event, EventBus, EventType
from maple_agent.executor.models import ExecutionResult, ExecutionStatus, ExecutionTask
from maple_agent.executor.provider import ExecutorProvider
from maple_agent.executor.safety import SafetyGate
from maple_agent.fusion.models import WorldState
from maple_agent.goal import GoalStateMachine, GoalStatus, GoalTransitionError
from maple_agent.goal.provider import GoalProvider
from maple_agent.goal.selector import RuleBasedGoalSelector
from maple_agent.logging_setup import TraceContext, new_id
from maple_agent.planner.adapter import serialize_for_planner
from maple_agent.planner.models import PlannerInput, PlanResult
from maple_agent.planner.provider import PlannerProvider
from maple_agent.providers.base import ErrorPayload
from maple_agent.quest_planner.models import QuestPlan
from maple_agent.quest_planner.planner import QuestPlanner
from maple_agent.quest_planner.resolver import QuestResolver
from maple_agent.quest_planner.validator import QuestPlanValidator
from maple_agent.vision.models import VisionState

logger = logging.getLogger("maple_agent.agent.loop")


class AgentLoopState(StrEnum):
    """Agent Loop 状态。"""

    IDLE = "IDLE"
    OBSERVING = "OBSERVING"
    CONTEXT_READY = "CONTEXT_READY"
    PLANNING = "PLANNING"
    VALIDATING = "VALIDATING"
    WAITING = "WAITING"
    REFLECTING = "REFLECTING"
    ERROR = "ERROR"


class IllegalTransitionError(RuntimeError):
    """非法状态跳转。"""


_TRANSITION_TABLE: dict[AgentLoopState, frozenset[AgentLoopState]] = {
    AgentLoopState.OBSERVING: frozenset({AgentLoopState.IDLE}),
    AgentLoopState.CONTEXT_READY: frozenset({AgentLoopState.OBSERVING}),
    AgentLoopState.PLANNING: frozenset({AgentLoopState.CONTEXT_READY}),
    AgentLoopState.VALIDATING: frozenset({AgentLoopState.PLANNING}),
    AgentLoopState.WAITING: frozenset({AgentLoopState.VALIDATING}),
    AgentLoopState.REFLECTING: frozenset({AgentLoopState.WAITING}),
    AgentLoopState.IDLE: frozenset(
        {AgentLoopState.REFLECTING, AgentLoopState.ERROR}
    ),
    AgentLoopState.ERROR: frozenset(
        {
            AgentLoopState.OBSERVING,
            AgentLoopState.CONTEXT_READY,
            AgentLoopState.PLANNING,
            AgentLoopState.VALIDATING,
            AgentLoopState.WAITING,
            AgentLoopState.REFLECTING,
        }
    ),
}


def validate_transition(current: AgentLoopState, target: AgentLoopState) -> None:
    allowed = _TRANSITION_TABLE.get(target, frozenset())
    if current not in allowed:
        raise IllegalTransitionError(
            f"非法状态跳转: {current.value} -> {target.value}"
        )


class AgentLoop:
    """只读 Agent Loop:Observe → Context → Plan → Validate → Wait → Reflect。"""

    def __init__(
        self,
        bus: EventBus,
        context_builder: ContextBuilder,
        planner: PlannerProvider,
        *,
        sessions_dir: str | Path = "sessions",
        retry_max: int = 1,
        goal_provider: GoalProvider | None = None,
        goal_selector: RuleBasedGoalSelector | None = None,
        quest_resolver: QuestResolver | None = None,
        quest_planner: QuestPlanner | None = None,
        quest_plan_validator: QuestPlanValidator | None = None,
        executor: ExecutorProvider | None = None,
        safety_gate: SafetyGate | None = None,
    ) -> None:
        self.bus = bus
        self.context_builder = context_builder
        self.planner = planner
        self.sessions_dir = Path(sessions_dir)
        self.retry_max = retry_max
        self.goal_provider = goal_provider
        self.goal_selector = goal_selector
        self.quest_resolver = quest_resolver
        self.quest_planner = quest_planner
        self.quest_plan_validator = quest_plan_validator or QuestPlanValidator()
        self.executor = executor
        self.safety_gate = safety_gate or SafetyGate()
        self._state = AgentLoopState.IDLE
        self._transitions: list[dict] = []
        self._last_trace_id = ""
        self.last_context: AgentContext | None = None
        self.last_plan: PlanResult | None = None
        self.last_error: str | None = None
        self.last_quest_plan: QuestPlan | None = None
        self.quest_plan_validation: str | None = None
        self.last_quest_plan_error: str | None = None
        self.last_execution: ExecutionResult | None = None
        self.execution_history: list[ExecutionResult] = []

    @property
    def state(self) -> AgentLoopState:
        return self._state

    def reset(self) -> None:
        """ERROR -> IDLE(异常恢复)。"""
        self._transition(AgentLoopState.IDLE)
        self.last_error = None

    def run_once(
        self,
        *,
        vision_state: VisionState | None = None,
        world_state: WorldState | None = None,
        runtime_state: str = "UNKNOWN",
        trace_id: str | None = None,
    ) -> PlanResult:
        """执行一轮只读循环;Planner 失败最多重试 retry_max 次。"""
        with TraceContext(trace_id=trace_id) as trace:
            tid = trace.trace_id
            self._last_trace_id = tid
            self._transitions = []
            self.last_error = None
            try:
                self._transition(AgentLoopState.OBSERVING)
                self._publish(EventType.OBSERVE_STARTED, None, tid)
                logger.info("observe started: trace=%s", tid)

                self._transition(AgentLoopState.CONTEXT_READY)
                context = self.context_builder.build(
                    vision_state=vision_state,
                    world_state=world_state,
                    runtime_state=runtime_state,
                    trace_id=tid,
                )
                self.last_context = context
                self._publish(EventType.CONTEXT_READY, context, tid)

                if self.goal_provider is not None and self.goal_selector is not None:
                    candidates = self.goal_provider.get_candidate_goals(trace_id=tid)
                    previous = self.goal_provider.get_active_goal(trace_id=tid)
                    selected = self.goal_selector.select(
                        context, candidates, trace_id=tid
                    )
                    if selected is not None:
                        if selected.status is GoalStatus.CREATED:
                            selected = GoalStateMachine().transition(
                                selected, GoalStatus.ACTIVE
                            )
                        self.goal_provider.activate(selected, trace_id=tid)
                        self._publish(EventType.GOAL_SELECTED, selected, tid)
                        if previous is None or previous.goal_id != selected.goal_id:
                            self._publish(EventType.GOAL_CHANGED, selected, tid)
                    goal_ctx = context.goal_context
                    if goal_ctx is None:
                        goal_ctx = GoalContext(trace_id=tid)
                    context = context.model_copy(
                        update={
                            "goal_context": goal_ctx.model_copy(
                                update={
                                    "active_goal": selected,
                                    "candidate_goals": candidates,
                                    "goal_history": list(goal_ctx.goal_history),
                                }
                            )
                        }
                    )
                    self.last_context = context
                    self._write_goal_replay(tid, candidates, selected, None)

                if self.quest_resolver is not None and self.quest_planner is not None:
                    context = self._run_quest_planning(context, tid)

                planner_input = serialize_for_planner(context)
                self._transition(AgentLoopState.PLANNING)
                plan = self._plan_with_retry(planner_input, tid)
                self.last_plan = plan

                self._transition(AgentLoopState.VALIDATING)
                self._publish(EventType.PLAN_VALIDATED, plan, tid)

                if self.executor is not None:
                    context = self._run_execution(plan, context, tid)

                self._transition(AgentLoopState.WAITING)
                self._transition(AgentLoopState.REFLECTING)
                logger.info("reflect: plan=%s steps=%d", plan.plan_id, len(plan.steps))

                self._transition(AgentLoopState.IDLE)
                self._write_replay(context, plan, None)
                return plan
            except Exception as exc:
                if self._state is not AgentLoopState.ERROR:
                    self._transition(AgentLoopState.ERROR)
                self.last_error = str(exc)
                self._publish(
                    EventType.LOOP_ERROR,
                    ErrorPayload(provider="agent.loop", message=str(exc)),
                    tid,
                )
                self._write_replay(self.last_context, None, str(exc))
                logger.error("agent loop failed: %s", exc)
                raise

    def _run_execution(
        self,
        plan: PlanResult,
        context: AgentContext,
        tid: str,
    ) -> AgentContext:
        """Execution Validation + Mock Execution(仅记录,不真实执行)。"""
        entries: list[tuple[ExecutionTask, object, ExecutionResult]] = []
        results: list[ExecutionResult] = []
        for step in plan.steps:
            task = ExecutionTask(
                execution_id=new_id(),
                plan_id=plan.plan_id,
                step_id=step.step_id,
                action=step.action,
                target=step.target,
                trace_id=tid,
            )
            self._publish(EventType.EXECUTION_CREATED, task, tid)
            safety = self.safety_gate.check(task, trace_id=tid)
            if not safety.allowed:
                blocked = ExecutionResult(
                    execution_id=task.execution_id,
                    status=ExecutionStatus.BLOCKED,
                    message=safety.reason,
                    trace_id=tid,
                )
                self._publish(EventType.EXECUTION_BLOCKED, blocked, tid)
                entries.append((task, safety, blocked))
                results.append(blocked)
                continue
            ready = task.model_copy(update={"status": ExecutionStatus.READY})
            try:
                result = self.executor.execute(ready)
            except Exception as exc:
                result = ExecutionResult(
                    execution_id=task.execution_id,
                    status=ExecutionStatus.FAILED,
                    message=str(exc),
                    trace_id=tid,
                )
                self._publish(EventType.EXECUTION_FAILED, result, tid)
            else:
                if result.status is ExecutionStatus.FAILED:
                    self._publish(EventType.EXECUTION_FAILED, result, tid)
                else:
                    self._publish(EventType.EXECUTION_COMPLETED, result, tid)
            entries.append((task, safety, result))
            results.append(result)
        self.last_execution = results[-1] if results else None
        self.execution_history.extend(results)
        self._write_execution_replay(tid, entries)
        previous = context.execution_context
        history = (
            list(previous.execution_history) + results
            if previous is not None
            else list(results)
        )
        updated = context.model_copy(
            update={
                "execution_context": ExecutionContext(
                    last_execution=self.last_execution,
                    execution_history=history,
                )
            }
        )
        self.last_context = updated
        return updated

    def _run_quest_planning(self, context: AgentContext, tid: str) -> AgentContext:
        """Goal → Quest → QuestPlan(仅计划,不执行);失败发布 FAILED 事件并继续。"""
        self.quest_plan_validation = None
        self.last_quest_plan_error = None
        goal = (
            context.goal_context.active_goal if context.goal_context is not None else None
        )
        quest = self.quest_resolver.resolve(goal, trace_id=tid)
        if quest is None:
            logger.info("quest planning skipped: 无 QUEST 目标或未找到任务")
            return context
        try:
            quest_plan = self.quest_planner.plan(
                quest,
                world_state=context.world_state,
                goal=goal,
                trace_id=tid,
            )
            self.quest_plan_validator.validate(quest_plan, quest=quest)
            self.last_quest_plan = quest_plan
            self.quest_plan_validation = "ok"
            self._publish(EventType.QUEST_PLAN_CREATED, quest_plan, tid)
            self._publish(EventType.QUEST_PLAN_VALIDATED, quest_plan, tid)
        except Exception as exc:
            self.last_quest_plan = None
            self.quest_plan_validation = "failed"
            self.last_quest_plan_error = str(exc)
            self._publish(
                EventType.QUEST_PLAN_FAILED,
                ErrorPayload(provider="quest_planner", message=str(exc)),
                tid,
            )
            self._write_quest_plan_replay(tid, None, f"failed: {exc}")
            logger.error("quest planning failed: %s", exc)
            return context

        previous = context.quest_plan_context
        history = (
            list(previous.plan_history) + [quest_plan]
            if previous is not None
            else [quest_plan]
        )
        updated = context.model_copy(
            update={
                "quest_plan_context": QuestPlanContext(
                    active_quest_plan=quest_plan,
                    current_step=0,
                    plan_history=history,
                )
            }
        )
        self.last_context = updated
        self._write_quest_plan_replay(tid, quest_plan, "ok")
        return updated

    def mark_goal_completed(
        self,
        goal_id: str,
        *,
        trace_id: str | None = None,
    ) -> None:
        """ACTIVE -> COMPLETED,发布 GOAL_COMPLETED(仅状态管理,不执行)。"""
        if self.goal_provider is None:
            raise GoalTransitionError("未配置 goal_provider")
        active = self.goal_provider.get_active_goal(trace_id=trace_id)
        if active is None or active.goal_id != goal_id:
            raise GoalTransitionError(f"目标 {goal_id} 非当前激活目标")
        completed = GoalStateMachine().transition(active, GoalStatus.COMPLETED)
        self.goal_provider.save_goal_status(completed, trace_id=trace_id)
        resolved_trace = trace_id or self._last_trace_id
        self._publish(EventType.GOAL_COMPLETED, completed, resolved_trace)
        candidates = self.goal_provider.get_candidate_goals(trace_id=trace_id)
        self._write_goal_replay(
            resolved_trace,
            candidates,
            completed,
            {"goal_id": goal_id, "to": GoalStatus.COMPLETED.value},
        )

    def _plan_with_retry(self, planner_input: PlannerInput, tid: str) -> PlanResult:
        attempt = 0
        while True:
            try:
                plan = self.planner.plan(planner_input)
                break
            except Exception as exc:
                attempt += 1
                if attempt > self.retry_max:
                    raise
                logger.warning(
                    "planner failed (attempt %d), retrying: %s", attempt, exc
                )
        self._publish(EventType.LOOP_PLAN_CREATED, plan, tid)
        return plan

    def _transition(self, target: AgentLoopState) -> None:
        validate_transition(self._state, target)
        record = {
            "from": self._state.value,
            "to": target.value,
            "at": datetime.now(UTC).isoformat(),
        }
        self._transitions.append(record)
        logger.info("agent loop state: %s -> %s", record["from"], record["to"])
        self._state = target

    def _publish(self, event_type: EventType, payload, trace_id: str) -> None:
        self.bus.publish(
            Event.create(
                event_type,
                source="agent.loop",
                payload=payload,
                trace_id=trace_id,
            )
        )

    def _write_replay(
        self,
        context: AgentContext | None,
        plan: PlanResult | None,
        error: str | None,
    ) -> None:
        trace_id = self._last_trace_id
        if not trace_id:
            return
        directory = self.sessions_dir / trace_id
        directory.mkdir(parents=True, exist_ok=True)
        payload = {
            "trace_id": trace_id,
            "final_state": self._state.value,
            "transitions": self._transitions,
            "context": context.model_dump(mode="json") if context else None,
            "planner_result": plan.model_dump(mode="json") if plan else None,
            "errors": [error] if error else [],
        }
        (directory / "agent_loop.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        if context is not None and context.goal_context is not None:
            (directory / "quest_context.json").write_text(
                json.dumps(
                    context.goal_context.model_dump(mode="json"),
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

    def _write_goal_replay(
        self,
        trace_id: str,
        candidates: list,
        selected,
        status_change: dict | None,
    ) -> None:
        directory = self.sessions_dir / trace_id
        directory.mkdir(parents=True, exist_ok=True)
        payload = {
            "trace_id": trace_id,
            "candidates": [
                item.model_dump(mode="json") if hasattr(item, "model_dump") else item
                for item in candidates
            ],
            "selected": (
                selected.model_dump(mode="json") if selected is not None else None
            ),
            "status_change": status_change,
        }
        (directory / "goal_context.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _write_quest_plan_replay(
        self,
        trace_id: str,
        plan: QuestPlan | None,
        validation_result: str,
    ) -> None:
        directory = self.sessions_dir / trace_id
        directory.mkdir(parents=True, exist_ok=True)
        payload = {
            "trace_id": trace_id,
            "goal_id": plan.goal_id if plan is not None else "",
            "quest_id": plan.quest_id if plan is not None else None,
            "steps": (
                [step.model_dump(mode="json") for step in plan.steps]
                if plan is not None
                else []
            ),
            "validation_result": validation_result,
        }
        (directory / "quest_plan.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def _write_execution_replay(
        self,
        trace_id: str,
        entries: list[tuple[ExecutionTask, object, ExecutionResult]],
    ) -> None:
        directory = self.sessions_dir / trace_id
        directory.mkdir(parents=True, exist_ok=True)
        payload = {
            "trace_id": trace_id,
            "executions": [
                {
                    "task": task.model_dump(mode="json"),
                    "safety_result": {
                        "allowed": safety.allowed,
                        "reason": safety.reason,
                        "mode": safety.mode,
                    },
                    "status": result.status.value,
                    "message": result.message,
                }
                for task, safety, result in entries
            ],
        }
        (directory / "execution.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
