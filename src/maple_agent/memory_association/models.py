"""Semantic Memory Association 数据模型(Phase 9-B,语义关联网络,只读)。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class SemanticRelationType(StrEnum):
    """语义关联类型。"""

    CAUSAL_LINK = "CAUSAL_LINK"
    FAILURE_PATTERN = "FAILURE_PATTERN"
    SUCCESS_PATTERN = "SUCCESS_PATTERN"
    PREFERENCE_ALIGNMENT = "PREFERENCE_ALIGNMENT"
    DECISION_IMPROVEMENT = "DECISION_IMPROVEMENT"
    WORLD_CONTEXT = "WORLD_CONTEXT"
    GOAL_SIMILARITY = "GOAL_SIMILARITY"


class SemanticMemoryRelation(BaseModel):
    """语义记忆关系(强类型,可序列化)。"""

    relation_id: str
    source_memory: str = ""
    target_memory: str = ""
    relation_type: SemanticRelationType
    confidence: float = Field(default=0.0, ge=0, le=1)
    reasoning: str = ""
    context: dict = Field(default_factory=dict)


class SemanticAssociationSummary(BaseModel):
    """语义关联摘要。"""

    strong_relations: int = 0
    risk_patterns: list[str] = Field(default_factory=list)
    successful_patterns: list[str] = Field(default_factory=list)
    preference_patterns: list[str] = Field(default_factory=list)
    improvement_hints: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0, le=1)


class SemanticMemoryReference(BaseModel):
    """语义记忆参考(REFERENCE ONLY,非 Action)。"""

    related_experiences: list[str] = Field(default_factory=list)
    failure_patterns: list[str] = Field(default_factory=list)
    decision_hints: list[str] = Field(default_factory=list)
    preference_alignment: list[str] = Field(default_factory=list)
    world_context: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0, le=1)
