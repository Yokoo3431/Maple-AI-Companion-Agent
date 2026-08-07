"""ContextBuilder:VisionState + WorldState + RuntimeState → AgentContext。"""

from __future__ import annotations

import logging

from maple_agent.context.models import AgentContext
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
    ) -> AgentContext:
        with TraceContext(trace_id=trace_id) as trace:
            context = AgentContext(
                world_state=world_state,
                runtime_state=runtime_state,
                vision_summary=vision_state.summary if vision_state else "",
                knowledge_profile=self.knowledge.game_profile if self.knowledge else "",
                trace_id=trace.trace_id,
            )
            logger.info(
                "context built: runtime=%s vision=%s profile=%s",
                runtime_state,
                bool(vision_state),
                context.knowledge_profile,
            )
            return context
