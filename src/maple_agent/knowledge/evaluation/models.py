"""Knowledge Evaluation 数据模型(Phase 4-D)。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class RetrievalCase(BaseModel):
    """检索评测用例。"""

    case_id: str
    query_text: str
    expected_entity_id: str
    expected_entity_type: str
    difficulty: str = ""
    source: str = ""


class EvaluationResult(BaseModel):
    """评测结果。"""

    total_cases: int = 0
    correct_top1: int = 0
    correct_topk: int = 0
    top1_accuracy: float = Field(default=0.0, ge=0, le=1)
    top3_recall: float = Field(default=0.0, ge=0, le=1)
    avg_rank: float = 0.0
    ranking_accuracy: float = Field(default=0.0, ge=0, le=1)
    precision: float = Field(default=0.0, ge=0, le=1)
    recall: float = Field(default=0.0, ge=0, le=1)
