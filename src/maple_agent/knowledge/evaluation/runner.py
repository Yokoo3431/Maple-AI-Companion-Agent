"""EvaluationRunner:检索评测(TOP-1 / TOP-K / 平均排名)。"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from maple_agent.knowledge.evaluation.models import EvaluationResult, RetrievalCase
from maple_agent.knowledge.retrieval import AliasIndex, EntityRanker
from maple_agent.knowledge_graph.graph import KnowledgeGraph

logger = logging.getLogger("maple_agent.knowledge")


def load_retrieval_cases(path: str | Path | None = None) -> list[RetrievalCase]:
    """加载评测用例(失败安全降级为空列表)。"""
    data_file = (
        Path(path)
        if path is not None
        else Path(__file__).resolve().parent / "data" / "retrieval_cases.json"
    )
    if not data_file.exists():
        return []
    try:
        raw = json.loads(data_file.read_text(encoding="utf-8"))
        return [
            RetrievalCase(
                case_id=item["id"],
                query_text=item["query"],
                expected_entity_id=item["expected"],
                expected_entity_type=item["type"],
                difficulty=item.get("difficulty", ""),
                source=item.get("source", "benchmark"),
            )
            for item in raw.get("cases", [])
        ]
    except Exception as exc:
        logger.warning("评测用例加载失败,降级为空: %s", exc)
        return []


class EvaluationRunner:
    def __init__(
        self,
        index: AliasIndex,
        ranker: EntityRanker | None = None,
        *,
        topk: int = 3,
    ) -> None:
        self.index = index
        self.ranker = ranker or EntityRanker()
        self.topk = topk

    @classmethod
    def from_graph(cls, graph: KnowledgeGraph) -> EvaluationRunner:
        return cls(AliasIndex.from_graph(graph))

    def run(self, cases: list[RetrievalCase]) -> EvaluationResult:
        if not cases:
            return EvaluationResult(total_cases=0)
        correct_top1 = 0
        correct_topk = 0
        ranks: list[int] = []
        for case in cases:
            candidates = self.index.search(
                case.query_text,
                entity_type=case.expected_entity_type,
            )
            ranked = self.ranker.rank(case.query_text, candidates, ocr_confidence=1.0)
            rank = len(ranked.candidates) + 1
            for position, candidate in enumerate(ranked.candidates, start=1):
                if (
                    f"{candidate.entity_type}_{candidate.entity_id}"
                    == case.expected_entity_id
                ):
                    rank = position
                    break
            ranks.append(rank)
            if rank == 1:
                correct_top1 += 1
            if rank <= self.topk:
                correct_topk += 1
        total = len(cases)
        avg_rank = sum(ranks) / total
        return EvaluationResult(
            total_cases=total,
            correct_top1=correct_top1,
            correct_topk=correct_topk,
            top1_accuracy=round(correct_top1 / total, 4),
            top3_recall=round(correct_topk / total, 4),
            avg_rank=round(avg_rank, 4),
            ranking_accuracy=round(1.0 / avg_rank, 4) if avg_rank else 0.0,
            precision=round(correct_top1 / total, 4),
            recall=round(correct_topk / total, 4),
        )
