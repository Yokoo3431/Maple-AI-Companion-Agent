"""ContextBuilder:VisionState + WorldState + RuntimeState → AgentContext。"""

from __future__ import annotations

import logging

from maple_agent.context.models import (
    AgentContext,
    GoalContext,
    KnowledgeState,
    MatchedEntity,
)
from maple_agent.fusion.models import WorldState
from maple_agent.logging_setup import TraceContext
from maple_agent.providers.knowledge import KnowledgeProvider
from maple_agent.vision.models import VisionState

logger = logging.getLogger("maple_agent.context")


class ContextBuilder:
    """把 Vision / Knowledge / Runtime 组装成 Planner 前上下文。"""

    def __init__(self, knowledge: KnowledgeProvider | None = None) -> None:
        self.knowledge = knowledge

    def build(
        self,
        *,
        vision_state: VisionState | None,
        world_state: WorldState | None,
        runtime_state: str,
        trace_id: str | None = None,
        goal_context: GoalContext | None = None,
    ) -> AgentContext:
        with TraceContext(trace_id=trace_id) as trace:
            resolved_goal = goal_context
            if resolved_goal is None and self.knowledge is not None:
                try:
                    available = self.knowledge.get_available_quests()
                except Exception:
                    available = []
                resolved_goal = GoalContext(
                    available_quests=available,
                    trace_id=trace.trace_id,
                )
            context = AgentContext(
                world_state=world_state,
                runtime_state=runtime_state,
                vision_summary=vision_state.summary if vision_state else "",
                knowledge_profile=self.knowledge.game_profile if self.knowledge else "",
                goal_context=resolved_goal,
                knowledge_state=self._build_knowledge_state(world_state),
                trace_id=trace.trace_id,
            )
            logger.info(
                "context built: runtime=%s vision=%s profile=%s",
                runtime_state,
                bool(vision_state),
                context.knowledge_profile,
            )
            return context

    def _build_knowledge_state(self, world_state) -> KnowledgeState | None:
        if world_state is None:
            return None
        entities: list[MatchedEntity] = []
        if world_state.current_map is not None:
            entities.append(
                MatchedEntity(
                    entity_type="map",
                    entity_id=world_state.current_map.map_id,
                    name=world_state.current_map.name,
                    confidence=world_state.confidence,
                )
            )
        for npc in world_state.known_npcs:
            entities.append(
                MatchedEntity(
                    entity_type="npc",
                    entity_id=npc.npc_id,
                    name=npc.name,
                    confidence=world_state.confidence,
                )
            )
        for monster in world_state.known_monsters:
            entities.append(
                MatchedEntity(
                    entity_type="monster",
                    entity_id=monster.monster_id,
                    name=monster.name,
                    confidence=world_state.confidence,
                )
            )
        return KnowledgeState(
            matched_entities=entities,
            confidence=world_state.confidence,
            source="knowledge_graph",
        )
