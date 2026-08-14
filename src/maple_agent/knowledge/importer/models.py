"""Import 数据模型(Phase 4-E)。"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field


class ImportSource(BaseModel):
    """导入来源。"""

    source_id: str
    source_type: str = "json"
    version: str = ""
    game_profile: str = ""
    server_profile: str = ""
    content_hash: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ImportResult(BaseModel):
    """导入结果。"""

    source: str = ""
    version: str = ""
    imported_maps: int = 0
    imported_npcs: int = 0
    imported_monsters: int = 0
    imported_items: int = 0
    imported_equipment: int = 0
    imported_quests: int = 0
    imported_story_lore: int = 0
    imported_relations: int = 0
    warnings: list[str] = Field(default_factory=list)
