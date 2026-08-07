"""Retrieval 数据模型(Phase 4-C)。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class CandidateEntity(BaseModel):
    """候选实体。"""

    entity_id: int | str
    entity_type: str
    text: str
    score: float = Field(default=0.0, ge=0, le=1)
    source: str = ""
    reason: str = ""


class RankingResult(BaseModel):
    """候选排序结果。"""

    query: str
    candidates: list[CandidateEntity] = Field(default_factory=list)
    best: CandidateEntity | None = None
    ocr_confidence: float = Field(default=0.0, ge=0, le=1)
    ranking_reason: str = ""
