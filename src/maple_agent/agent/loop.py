"""Agent Loop 状态机与编排(Phase 1.8-B,只读;无 Executor / Input)。"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path

from maple_agent.context.builder import ContextBuilder
from maple_agent.context.models import AgentContext
from maple_agent.events import Event, EventBus, EventType
from maple_agent.fusion.models import WorldState
from maple_agent.logging_setup import TraceContext
from maple_agent.planner.adapter import serialize_for_planner
from maple_agent.planner.models import PlannerInput, PlanResult
from maple_agent.planner.provider import PlannerProvider
from maple_agent.providers.base import ErrorPayload
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
    ) -> None:
        self.bus = bus
        self.context_builder = context_builder
        self.planner = planner
        self.sessions_dir = Path(sessions_dir)
        self.retry_max = retry_max
        self._state = AgentLoopState.IDLE
        self._transitions: list[dict] = []
        self._last_trace_id = ""
        self.last_context: AgentContext | None = None
        self.last_plan: PlanResult | None = None
        self.last_error: str | None = None

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

                planner_input = serialize_for_planner(context)
                self._transition(AgentLoopState.PLANNING)
                plan = self._plan_with_retry(planner_input, tid)
                self.last_plan = plan

                self._transition(AgentLoopState.VALIDATING)
                self._publish(EventType.PLAN_VALIDATED, plan, tid)

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
