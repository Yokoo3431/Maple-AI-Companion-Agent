"""Deterministic context reasoning rule constants."""

from __future__ import annotations

from maple_agent.game_state.models import EntityLifecycle
from maple_agent.knowledge_graph.models import RelationType

ACTIVE_LIFECYCLE = EntityLifecycle.VISIBLE
DEFAULT_RELATION_CONFIDENCE_THRESHOLD = 0.7

LOCATION_TYPES = {"map", "map_label", "location"}
NPC_TYPES = {"npc", "character"}
QUEST_TYPES = {"quest", "quest_context"}
ITEM_TYPES = {"item", "equipment", "inventory", "inventory_item"}

QUEST_RELATIONS = {RelationType.CONTAINS, RelationType.GIVES}
