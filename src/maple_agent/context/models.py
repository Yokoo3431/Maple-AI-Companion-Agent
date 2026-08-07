"""AgentContext 领域模型。"""

from __future__ import annotations

from pydantic import BaseModel

from maple_agent.fusion.models import WorldState


class AgentContext(BaseModel):
    """Planner 前统一上下文(Vision + Knowledge + Runtime)。"""

    world_state: WorldState | None = None
    runtime_state: str = ""
    vision_summary: str = ""
    knowledge_profile: str = ""
    trace_id: str = ""
