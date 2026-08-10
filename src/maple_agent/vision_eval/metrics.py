"""视觉评价指标:OCR / Entity / Consistency / Confidence(0-1)。"""

from __future__ import annotations

from maple_agent.vision_eval.models import VisionMetric


def ocr_quality_score(text: str, confidence: float) -> VisionMetric:
    """OCR 质量:置信度(0.6) + 文本长度(0.4) + 空检测。"""
    stripped = text.strip()
    if not stripped:
        return VisionMetric(
            metric_name="ocr_quality",
            score=0.0,
            reason="OCR 文本为空",
        )
    confidence_score = max(0.0, min(1.0, confidence))
    length = len(stripped)
    if length < 3:
        length_score = 0.1
    elif length <= 50:
        length_score = 0.4
    else:
        length_score = 0.2
    score = confidence_score * 0.6 + length_score
    return VisionMetric(
        metric_name="ocr_quality",
        score=round(max(0.0, min(1.0, score)), 4),
        reason=f"confidence={confidence_score:.2f} text_len={length}",
    )


def entity_quality_score(
    entities: list[str],
    match_rate: float,
) -> VisionMetric:
    """实体质量:数量(0.4) + 知识匹配率(0.6)。"""
    if not entities:
        return VisionMetric(
            metric_name="entity_quality",
            score=0.0,
            reason="无可见实体",
        )
    count_score = min(1.0, len(entities) / 5)
    score = count_score * 0.4 + max(0.0, min(1.0, match_rate)) * 0.6
    return VisionMetric(
        metric_name="entity_quality",
        score=round(max(0.0, min(1.0, score)), 4),
        reason=f"entities={len(entities)} match_rate={match_rate:.2f}",
    )


def consistency_score(
    map_name: str,
    entities: list[str],
    known_entities: list[str],
) -> VisionMetric:
    """内部一致性:实体是否属于当前地图。"""
    if not map_name and not entities:
        return VisionMetric(
            metric_name="consistency",
            score=0.8,
            reason="无信息可判定",
        )
    if not entities:
        return VisionMetric(
            metric_name="consistency",
            score=0.8,
            reason="无实体可交叉验证",
        )
    if not known_entities:
        return VisionMetric(
            metric_name="consistency",
            score=0.6,
            reason="知识库缺少地图实体,无法交叉验证",
        )
    matched = sum(1 for entity in entities if entity in known_entities)
    ratio = matched / len(entities)
    score = 0.3 + 0.7 * ratio
    reason = f"{matched}/{len(entities)} 实体与地图 {map_name or '-'} 匹配"
    return VisionMetric(
        metric_name="consistency",
        score=round(max(0.0, min(1.0, score)), 4),
        reason=reason,
    )


def confidence_quality_score(confidence: float) -> VisionMetric:
    """整体置信度:>=0.8 满分,0.5-0.8 中,<0.5 低。"""
    if confidence >= 0.8:
        score = 1.0
    elif confidence >= 0.5:
        score = 0.6
    else:
        score = 0.3
    return VisionMetric(
        metric_name="confidence",
        score=score,
        reason=f"confidence={confidence:.2f}",
    )
