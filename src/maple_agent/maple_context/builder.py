"""MapleContextBuilder:AgentLoopContext -> MapleCompanionContextReference(只读)。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from maple_agent.architecture import TRACE_SCHEMA_VERSION
from maple_agent.maple_context.cognitive import MapleCognitiveContextBuilder
from maple_agent.maple_context.goal import MapleGoalContextBuilder
from maple_agent.maple_context.models import MapleCompanionContextReference
from maple_agent.maple_context.player import MaplePlayerContextBuilder
from maple_agent.maple_context.world import MapleWorldContextBuilder

if TYPE_CHECKING:
    from maple_agent.agent_loop.models import AgentLoopContext


class MapleContextBuilder:
    """整合既有认知模块为统一 Maple 上下文参考。"""

    def __init__(
        self,
        *,
        player_builder: MaplePlayerContextBuilder | None = None,
        world_builder: MapleWorldContextBuilder | None = None,
        goal_builder: MapleGoalContextBuilder | None = None,
        cognitive_builder: MapleCognitiveContextBuilder | None = None,
    ) -> None:
        self.player_builder = player_builder or MaplePlayerContextBuilder()
        self.world_builder = world_builder or MapleWorldContextBuilder()
        self.goal_builder = goal_builder or MapleGoalContextBuilder()
        self.cognitive_builder = (
            cognitive_builder or MapleCognitiveContextBuilder()
        )
        self.last_reference: MapleCompanionContextReference | None = None

    def build(
        self,
        *,
        agent_context: AgentLoopContext,
        player_id: str = "maple-player",
        trace_id: str = "",
    ) -> MapleCompanionContextReference:
        player = self.player_builder.build(
            player_id=player_id,
            environment_state=agent_context.environment_state,
        )
        world_events = (
            agent_context.environment_history.timeline
            if agent_context.environment_history is not None
            else None
        )
        environment_risk = (
            agent_context.environment_risk_reference.risk_level
            if agent_context.environment_risk_reference is not None
            else ""
        )
        world = self.world_builder.build(
            environment_state=agent_context.environment_state,
            world_prediction=agent_context.environment_prediction,
            world_events=world_events,
            environment_risk=environment_risk,
        )
        goal = self.goal_builder.build(
            active_goal=agent_context.goal_state,
            goal_schedule=agent_context.goal_schedule,
            planning_reference=agent_context.environment_planning_reference,
            decision_reference=agent_context.decision_reference,
        )
        cognitive = self.cognitive_builder.build(
            decision_reference=agent_context.decision_reference,
            human_alignment=agent_context.human_alignment_reference,
            memory_reference=agent_context.memory_reference,
            semantic_memory_reference=(
                agent_context.semantic_memory_reference
            ),
            failure_reference=agent_context.failure_prevention_reference,
        )
        confidence = self._confidence(player, world, goal, cognitive)
        summary = self._summary(player, world, goal, cognitive)
        reference = MapleCompanionContextReference(
            player_context=player,
            world_context=world,
            goal_context=goal,
            cognitive_context=cognitive,
            summary=summary,
            confidence=confidence,
            trace_id=trace_id or agent_context.trace_id,
        )
        self.last_reference = reference
        return reference

    @staticmethod
    def _confidence(
        player,
        world,
        goal,
        cognitive,
    ) -> float:
        values = [
            player.confidence,
            world.confidence,
            goal.confidence,
            cognitive.confidence,
        ]
        present = [value for value in values if value > 0]
        if not present:
            return 0.0
        return round(sum(present) / len(present), 4)

    @staticmethod
    def _summary(player, world, goal, cognitive) -> str:
        parts: list[str] = []
        if player.location:
            parts.append(f"玩家位于 {player.location}")
        if goal.active_goal:
            parts.append(f"目标: {goal.active_goal}")
        if world.environment_risk:
            parts.append(f"环境风险: {world.environment_risk}")
        if cognitive.confidence:
            parts.append(f"认知置信: {cognitive.confidence:.2f}")
        return "。".join(parts) or "认知上下文未就绪"


def save_maple_context_trace(
    sessions_dir: str | Path,
    trace_id: str,
    *,
    reference: MapleCompanionContextReference,
    validation: str,
) -> None:
    """写入 maple_context_trace.json(统一 Replay)。"""
    directory = Path(sessions_dir) / trace_id
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "player_context": (
            reference.player_context.model_dump(mode="json")
            if reference.player_context is not None
            else {}
        ),
        "world_context": (
            reference.world_context.model_dump(mode="json")
            if reference.world_context is not None
            else {}
        ),
        "goal_context": (
            reference.goal_context.model_dump(mode="json")
            if reference.goal_context is not None
            else {}
        ),
        "cognitive_context": (
            reference.cognitive_context.model_dump(mode="json")
            if reference.cognitive_context is not None
            else {}
        ),
        "confidence": reference.confidence,
        "validation": validation,
    }
    (directory / "maple_context_trace.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
