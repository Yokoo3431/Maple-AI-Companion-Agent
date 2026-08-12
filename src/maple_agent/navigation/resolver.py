"""TargetResolver:目标解析(NPC/地图/任务区域,确定性)。"""

from __future__ import annotations

from maple_agent.spatial_world.models import SpatialWorldReference
from maple_agent.world_knowledge.models import WorldKnowledgeReference


class TargetResolver:
    """把目标名称解析为位置/地图参考。"""

    def resolve(
        self,
        target: str,
        *,
        spatial: SpatialWorldReference | None = None,
        world_knowledge: WorldKnowledgeReference | None = None,
    ) -> dict:
        if spatial is not None:
            for npc in spatial.npc_positions:
                if npc.get("name") == target:
                    return {
                        "kind": "NPC",
                        "map": spatial.current_map,
                        "location": {
                            "x": npc.get("x", 0),
                            "y": npc.get("y", 0),
                        },
                    }
            for zone in spatial.quest_targets:
                if zone.get("quest") == target:
                    return {
                        "kind": "QUEST_TARGET",
                        "map": spatial.current_map,
                        "location": {
                            "x": zone.get("x", 0),
                            "y": zone.get("y", 0),
                        },
                    }
        if (
            world_knowledge is not None
            and target in world_knowledge.known_maps
        ):
            return {"kind": "MAP", "map": target, "location": {}}
        return {"kind": "UNKNOWN", "map": "", "location": {}}
