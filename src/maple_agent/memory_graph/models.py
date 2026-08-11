"""Cognitive Memory Graph 数据模型(Phase 9-A,统一记忆图谱,只读)。"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class MemoryType(StrEnum):
    """记忆类型。"""

    EXPERIENCE = "EXPERIENCE"
    FAILURE = "FAILURE"
    WORLD = "WORLD"
    PREFERENCE = "PREFERENCE"
    DECISION = "DECISION"


class MemoryRelationType(StrEnum):
    """记忆关系类型。"""

    CAUSED_BY = "CAUSED_BY"
    SIMILAR_TO = "SIMILAR_TO"
    IMPROVED_BY = "IMPROVED_BY"
    PREFERRED_AFTER = "PREFERRED_AFTER"
    FAILED_AFTER = "FAILED_AFTER"


class MemoryRelation(BaseModel):
    """记忆关系。"""

    relation_type: MemoryRelationType
    target_id: str = ""


class MemoryNode(BaseModel):
    """统一记忆节点。"""

    memory_id: str
    memory_type: MemoryType
    source: str = ""
    content: str = ""
    context: dict = Field(default_factory=dict)
    confidence: float = Field(default=0.0, ge=0, le=1)
    importance: float = Field(default=0.0, ge=0, le=1)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    relations: list[MemoryRelation] = Field(default_factory=list)


class RelevantMemoryReference(BaseModel):
    """相关记忆参考(只读)。"""

    relevant_memories: list[MemoryNode] = Field(default_factory=list)
    similar_experiences: list[MemoryNode] = Field(default_factory=list)
    related_failures: list[MemoryNode] = Field(default_factory=list)
    environment_history: list[MemoryNode] = Field(default_factory=list)
    preference_hints: list[MemoryNode] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0, le=1)
    reasoning: list[str] = Field(default_factory=list)
