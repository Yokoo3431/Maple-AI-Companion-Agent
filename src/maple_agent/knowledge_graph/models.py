"""Knowledge Graph 节点与关系模型(Phase 4-A)。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class RelationType(StrEnum):
    """关系类型。"""

    CONTAINS = "CONTAINS"
    LOCATED_AT = "LOCATED_AT"
    SPAWNS = "SPAWNS"
    GIVES = "GIVES"
    REQUIRES = "REQUIRES"
    REWARD = "REWARD"
    REWARDS = "REWARDS"
    DROPS = "DROPS"
    CONNECTED_TO = "CONNECTED_TO"
    USES = "USES"
    EQUIPPED_BY = "EQUIPPED_BY"
    PART_OF = "PART_OF"
    ADVANCES = "ADVANCES"
    REVEALS = "REVEALS"


class KnowledgeEntityProvenance(BaseModel):
    """Per-entity provenance carried through the generic import pipeline."""

    source_id: str = ""
    source_type: str = ""
    source_reference: str = ""
    source_name: str = ""
    game_profile: str = ""
    server_profile: str = ""
    data_version: str = ""
    snapshot_version: str = ""
    content_hash: str = ""
    adapter_name: str = ""
    adapter_version: str = ""


class MapNode(BaseModel):
    """地图节点。"""

    map_id: int | str
    name: str
    aliases: list[str] = Field(default_factory=list)
    region: str = ""
    parent_region: str = ""
    connections: list[int | str] = Field(default_factory=list)
    provenance: KnowledgeEntityProvenance = Field(default_factory=KnowledgeEntityProvenance)
    confidence: float = Field(default=0.0, ge=0, le=1)
    version: str = ""


class NPCNode(BaseModel):
    """NPC 节点。"""

    npc_id: int | str
    name: str
    aliases: list[str] = Field(default_factory=list)
    location: int | str | None = None
    description: str = ""
    provenance: KnowledgeEntityProvenance = Field(default_factory=KnowledgeEntityProvenance)
    confidence: float = Field(default=0.0, ge=0, le=1)
    version: str = ""


class MonsterNode(BaseModel):
    """怪物节点。"""

    monster_id: int | str
    name: str
    aliases: list[str] = Field(default_factory=list)
    location: int | str | None = None
    level: int | None = None
    drops: list[int | str] = Field(default_factory=list)
    provenance: KnowledgeEntityProvenance = Field(default_factory=KnowledgeEntityProvenance)
    confidence: float = Field(default=0.0, ge=0, le=1)
    version: str = ""


class ItemNode(BaseModel):
    """物品节点。"""

    item_id: int | str
    name: str
    aliases: list[str] = Field(default_factory=list)
    provenance: KnowledgeEntityProvenance = Field(default_factory=KnowledgeEntityProvenance)
    confidence: float = Field(default=0.0, ge=0, le=1)
    version: str = ""


class EquipmentNode(BaseModel):
    """Equipment entity for the semantic graph foundation."""

    equipment_id: int | str
    name: str
    aliases: list[str] = Field(default_factory=list)
    slot: str = ""
    level: int | None = None
    attributes: dict[str, str | int | float | bool] = Field(default_factory=dict)
    provenance: KnowledgeEntityProvenance = Field(default_factory=KnowledgeEntityProvenance)
    confidence: float = Field(default=0.0, ge=0, le=1)
    version: str = ""


class QuestNode(BaseModel):
    """Quest entity for semantic context references."""

    quest_id: int | str
    name: str
    aliases: list[str] = Field(default_factory=list)
    description: str = ""
    npc_ids: list[int | str] = Field(default_factory=list)
    map_ids: list[int | str] = Field(default_factory=list)
    item_ids: list[int | str] = Field(default_factory=list)
    monster_ids: list[int | str] = Field(default_factory=list)
    provenance: KnowledgeEntityProvenance = Field(default_factory=KnowledgeEntityProvenance)
    confidence: float = Field(default=0.0, ge=0, le=1)
    version: str = ""


class StoryLoreNode(BaseModel):
    """Sanitized story/lore entity for contextual resolution."""

    lore_id: int | str
    name: str
    aliases: list[str] = Field(default_factory=list)
    description: str = ""
    topic: str = ""
    provenance: KnowledgeEntityProvenance = Field(default_factory=KnowledgeEntityProvenance)
    confidence: float = Field(default=0.0, ge=0, le=1)
    version: str = ""


class Relation(BaseModel):
    """实体关系及其可审计来源。"""

    source: str
    source_id: int | str
    target: str
    target_id: int | str
    relation_type: RelationType
    provenance: KnowledgeEntityProvenance = Field(
        default_factory=KnowledgeEntityProvenance
    )
    confidence: float = Field(default=0.0, ge=0, le=1)


class RelationReference(BaseModel):
    """Read-only query result retaining edge semantics and provenance."""

    entity_type: str
    entity_id: int | str
    name: str
    relation_type: RelationType
    confidence: float = Field(default=0.0, ge=0, le=1)
    provenance: KnowledgeEntityProvenance = Field(
        default_factory=KnowledgeEntityProvenance
    )
