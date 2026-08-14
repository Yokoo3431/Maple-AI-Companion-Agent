"""Game State Understanding 数据模型(Phase 11-B,结构化 Maple 状态,只读)。"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field

from maple_agent.hybrid_vision.models import (
    PerceptionEvidence,
    ResolutionCandidate,
)


class PlayerStateReference(BaseModel):
    """玩家状态参考。"""

    hp: float | None = Field(default=None, ge=0, le=1)
    mp: float | None = Field(default=None, ge=0, le=1)
    level_reference: int | None = None
    job_reference: str = ""
    position_reference: dict = Field(default_factory=dict)


class CurrentObservation(BaseModel):
    """Evidence-preserving input to semantic state resolution."""

    observation_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    evidence: list[PerceptionEvidence] = Field(default_factory=list)
    player_status: PlayerStateReference | None = None


class MapStateReference(BaseModel):
    """地图状态参考。"""

    map_name: str = ""
    known_map: bool = False
    exits_reference: list[str] = Field(default_factory=list)


class EntityStateReference(BaseModel):
    """可见实体状态参考。"""

    name: str
    type: str = "UNKNOWN"
    position_reference: dict = Field(default_factory=dict)
    confidence: float = Field(default=0.0, ge=0, le=1)


class QuestStateSnapshot(BaseModel):
    """任务状态快照(参考)。"""

    active_quests: list[str] = Field(default_factory=list)
    available_quests: list[str] = Field(default_factory=list)
    completed_reference: list[str] = Field(default_factory=list)


class GameStateReference(BaseModel):
    """结构化 Maple 游戏状态(不是 Action)。"""

    state_id: str
    player_state: PlayerStateReference | None = None
    current_map: MapStateReference | None = None
    visible_entities: list[EntityStateReference] = Field(
        default_factory=list
    )
    quest_state: QuestStateSnapshot | None = None
    combat_state: str = "UNKNOWN"
    confidence: float = Field(default=0.0, ge=0, le=1)
    reasoning: list[str] = Field(default_factory=list)


class SemanticEntityReference(BaseModel):
    """Resolved canonical reference linked back to observation evidence."""

    canonical_id: str
    entity_type: str
    display_name: str
    confidence: float = Field(default=0.0, ge=0, le=1)
    evidence_ids: list[str] = Field(default_factory=list)
    source: str = ""
    version: str = ""


class SemanticGameState(BaseModel):
    """Read-only semantic state; no action or execution fields."""

    state_id: str
    observation_id: str
    location: SemanticEntityReference | None = None
    player_status: PlayerStateReference | None = None
    nearby_entities: list[SemanticEntityReference] = Field(default_factory=list)
    quest_context: list[SemanticEntityReference] = Field(default_factory=list)
    inventory_references: list[SemanticEntityReference] = Field(default_factory=list)
    resolution_candidates: list[ResolutionCandidate] = Field(default_factory=list)
    unresolved_evidence_ids: list[str] = Field(default_factory=list)
    evidence: list[PerceptionEvidence] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0, le=1)
    reasoning: list[str] = Field(default_factory=list)
