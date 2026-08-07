"""EntityRanker:final_score = ocr_confidence + text_similarity + context_score。"""

from __future__ import annotations

from maple_agent.knowledge.retrieval.models import CandidateEntity, RankingResult


class EntityRanker:
    def rank(
        self,
        query: str,
        candidates: list[CandidateEntity],
        *,
        ocr_confidence: float = 1.0,
        context_hits: set[str] | None = None,
    ) -> RankingResult:
        context_hits = context_hits or set()
        ranked: list[CandidateEntity] = []
        for candidate in candidates:
            similarity = candidate.score
            context_score = 0.1 if candidate.entity_type in context_hits else 0.0
            final = round(
                ocr_confidence * 0.5 + similarity * 0.4 + context_score,
                4,
            )
            ranked.append(
                candidate.model_copy(
                    update={
                        "score": final,
                        "reason": (
                            f"{candidate.reason};context={candidate.entity_type}"
                            if context_score > 0
                            else candidate.reason
                        ),
                    }
                )
            )
        ranked.sort(key=lambda item: item.score, reverse=True)
        best = ranked[0] if ranked else None
        reason = (
            f"top={best.text}({best.source}) score={best.score}"
            if best is not None
            else "no candidate"
        )
        return RankingResult(
            query=query,
            candidates=ranked,
            best=best,
            ocr_confidence=ocr_confidence,
            ranking_reason=reason,
        )
