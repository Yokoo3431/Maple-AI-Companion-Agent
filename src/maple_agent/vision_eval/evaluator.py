"""VisionEvaluator:ObservationFrame + ObservationState + KnowledgeState -> 质量评分。"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from pathlib import Path

from maple_agent.context.models import KnowledgeState
from maple_agent.logging_setup import TraceContext, new_id
from maple_agent.observation.models import ObservationFrame, ObservationState
from maple_agent.providers.knowledge import KnowledgeProvider
from maple_agent.vision_eval.metrics import (
    confidence_quality_score,
    consistency_score,
    entity_quality_score,
    ocr_quality_score,
)
from maple_agent.vision_eval.models import RiskLevel, VisionEvaluationResult

logger = logging.getLogger("maple_agent.vision_eval")


class VisionEvaluator:
    """评估观察输出的识别可信度 / 一致性 / 错误风险(只读)。"""

    def __init__(
        self,
        *,
        knowledge: KnowledgeProvider | None = None,
        sessions_dir: str | Path = "sessions",
    ) -> None:
        self.knowledge = knowledge
        self.sessions_dir = Path(sessions_dir)
        self.last_result: VisionEvaluationResult | None = None

    def evaluate(
        self,
        *,
        frame: ObservationFrame,
        state: ObservationState | None = None,
        knowledge_state: KnowledgeState | None = None,
        trace_id: str | None = None,
    ) -> VisionEvaluationResult:
        """Overall = OCR*0.3 + Entity*0.3 + Consistency*0.3 + Confidence*0.1。"""
        with TraceContext(trace_id=trace_id) as trace:
            ocr_metric = ocr_quality_score(frame.ocr_text, frame.confidence)
            entities = state.visible_entities if state is not None else []
            known_entities = self._known_entities(
                state.map_name if state is not None else ""
            )
            match_rate = self._match_rate(entities, known_entities)
            entity_metric = entity_quality_score(entities, match_rate)
            consistency_metric = consistency_score(
                state.map_name if state is not None else "",
                entities,
                known_entities,
            )
            confidence_metric = confidence_quality_score(frame.confidence)
            overall = round(
                ocr_metric.score * 0.3
                + entity_metric.score * 0.3
                + consistency_metric.score * 0.3
                + confidence_metric.score * 0.1,
                4,
            )
            issues, recommendations = self._issues(
                frame,
                ocr_metric.score,
                entity_metric.score,
                consistency_metric.score,
                match_rate,
                entities,
                known_entities,
            )
            risk_level = self._risk_level(overall)
            result = VisionEvaluationResult(
                evaluation_id=new_id(),
                frame_id=frame.frame_id,
                overall_score=overall,
                ocr_score=ocr_metric.score,
                entity_score=entity_metric.score,
                consistency_score=consistency_metric.score,
                confidence_score=confidence_metric.score,
                risk_level=risk_level,
                issues=issues,
                recommendations=recommendations,
                timestamp=datetime.now(UTC),
            )
            self.last_result = result
            if trace.trace_id:
                self._write_replay(result, trace.trace_id)
            logger.info(
                "vision eval: frame=%s overall=%.4f risk=%s",
                frame.frame_id,
                overall,
                risk_level.value,
            )
            return result

    def _known_entities(self, map_name: str) -> list[str]:
        """当前地图知识库实体(用于一致性/匹配率)。"""
        if self.knowledge is None or not map_name:
            return []
        try:
            map_info = self.knowledge.get_map(map_name)
            if map_info is None:
                return []
            entities: list[str] = []
            try:
                entities.extend(
                    npc.name
                    for npc in self.knowledge.get_npcs_by_map(map_info.map_id)
                )
            except Exception:
                pass
            try:
                entities.extend(
                    monster.name
                    for monster in self.knowledge.get_monsters_by_map(
                        map_info.map_id
                    )
                )
            except Exception:
                pass
            return entities
        except Exception:
            return []

    @staticmethod
    def _match_rate(entities: list[str], known_entities: list[str]) -> float:
        if not entities:
            return 0.0
        matched = sum(1 for entity in entities if entity in known_entities)
        return round(matched / len(entities), 4)

    @staticmethod
    def _risk_level(overall: float) -> RiskLevel:
        if overall >= 0.8:
            return RiskLevel.LOW
        if overall >= 0.5:
            return RiskLevel.MEDIUM
        return RiskLevel.HIGH

    @staticmethod
    def _issues(
        frame: ObservationFrame,
        ocr_score: float,
        entity_score: float,
        consistency: float,
        match_rate: float,
        entities: list[str],
        known_entities: list[str],
    ) -> tuple[list[str], list[str]]:
        issues: list[str] = []
        recommendations: list[str] = []
        if not frame.ocr_text.strip():
            issues.append("OCR 文本为空")
            recommendations.append("检查截图质量或 OCR 适配")
        elif ocr_score < 0.5:
            issues.append("OCR 质量偏低")
        if entity_score < 0.5:
            issues.append("实体识别质量偏低")
            recommendations.append("扩充知识库实体或改进实体匹配")
        if consistency < 0.6:
            issues.append("观察内部不一致")
            recommendations.append("交叉验证地图与实体来源")
        if entities and match_rate < 0.5:
            issues.append(f"实体知识匹配率低: {match_rate:.0%}")
        if entities and not known_entities:
            recommendations.append("补充当前地图实体知识")
        return issues, recommendations

    def _write_replay(
        self,
        result: VisionEvaluationResult,
        trace_id: str,
    ) -> None:
        directory = self.sessions_dir / trace_id
        directory.mkdir(parents=True, exist_ok=True)
        payload = {
            "frame_id": result.frame_id,
            "overall_score": result.overall_score,
            "ocr_score": result.ocr_score,
            "entity_score": result.entity_score,
            "consistency_score": result.consistency_score,
            "confidence_score": result.confidence_score,
            "risk_level": result.risk_level.value,
            "issues": result.issues,
            "recommendations": result.recommendations,
            "timestamp": result.timestamp.isoformat(),
        }
        (directory / "vision_evaluation.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
