"""RealVisionReadiness:由 Benchmark 自动生成就绪参考(禁止手工 PASSED)。"""

from __future__ import annotations

from maple_agent.real_vision.models import (
    RealVisionBenchmarkResult,
    RealVisionReadinessPolicy,
)
from maple_agent.safety_vnext.models import (
    ReadinessStatus,
    RealVisionReadinessReference,
)


def build_real_vision_readiness(
    metrics: RealVisionBenchmarkResult,
    *,
    policy: RealVisionReadinessPolicy | None = None,
    real_client_tested: bool = False,
    capture_provider: str = "",
    ocr_provider: str = "",
    capture_available: bool = True,
    ocr_available: bool = True,
) -> RealVisionReadinessReference:
    """根据实测指标生成 readiness;任何门槛未真实达标即为 NOT_READY。"""
    policy = policy or RealVisionReadinessPolicy()
    reasons: list[str] = []
    if not real_client_tested:
        reasons.append("real client not tested")
    if not capture_available:
        reasons.append("capture provider unavailable")
    if not ocr_available:
        reasons.append("OCR provider unavailable")
    if metrics.sample_count < policy.minimum_sample_count:
        reasons.append(
            f"insufficient samples: {metrics.sample_count} "
            f"< {policy.minimum_sample_count}"
        )
    if (
        metrics.capture_success_rate is not None
        and metrics.capture_success_rate < policy.capture_success_rate
    ):
        reasons.append("capture success below threshold")
    if (
        metrics.map_accuracy is not None
        and metrics.map_accuracy < policy.map_accuracy
    ):
        reasons.append("map accuracy below threshold")
    hp_mp_values = [
        value
        for value in (metrics.hp_mae, metrics.mp_mae)
        if value is not None
    ]
    hp_mp_accuracy = (
        round(1.0 - sum(hp_mp_values) / len(hp_mp_values), 4)
        if hp_mp_values
        else None
    )
    if hp_mp_accuracy is not None and hp_mp_accuracy < policy.hp_mp_accuracy:
        reasons.append("hp/mp accuracy below threshold")
    if (
        metrics.quest_state_accuracy is not None
        and metrics.quest_state_accuracy < policy.quest_state_accuracy
    ):
        reasons.append("quest state accuracy below threshold")
    if (
        metrics.ui_signal_accuracy is not None
        and metrics.ui_signal_accuracy < policy.ui_signal_accuracy
    ):
        reasons.append("ui signal accuracy below threshold")
    entity_values = [
        value
        for value in (
            metrics.npc_precision,
            metrics.npc_recall,
            metrics.monster_precision,
            metrics.monster_recall,
            metrics.item_precision,
            metrics.item_recall,
        )
        if value is not None
    ]
    entity_accuracy = (
        round(sum(entity_values) / len(entity_values), 4)
        if entity_values
        else None
    )
    if (
        policy.entity_detection_required
        and entity_accuracy is None
    ):
        reasons.append("entity detection not evaluated")
    calibration_values = [
        bucket.accuracy
        for bucket in metrics.confidence_buckets
        if bucket.accuracy is not None
    ]
    calibration = (
        round(sum(calibration_values) / len(calibration_values), 4)
        if calibration_values
        else None
    )
    if calibration is not None and calibration < policy.confidence_calibration:
        reasons.append("confidence calibration below threshold")
    has_samples = metrics.sample_count > 0
    passed = (
        real_client_tested
        and capture_available
        and ocr_available
        and metrics.sample_count >= policy.minimum_sample_count
        and metrics.capture_success_rate is not None
        and metrics.capture_success_rate >= policy.capture_success_rate
        and metrics.map_accuracy is not None
        and metrics.map_accuracy >= policy.map_accuracy
        and hp_mp_accuracy is not None
        and hp_mp_accuracy >= policy.hp_mp_accuracy
        and metrics.quest_state_accuracy is not None
        and metrics.quest_state_accuracy >= policy.quest_state_accuracy
        and metrics.ui_signal_accuracy is not None
        and metrics.ui_signal_accuracy >= policy.ui_signal_accuracy
        and (calibration is not None)
        and calibration >= policy.confidence_calibration
        and not (
            policy.entity_detection_required and entity_accuracy is None
        )
    )
    if passed:
        status = ReadinessStatus.PASSED
    elif has_samples and real_client_tested:
        status = ReadinessStatus.FOUNDATION_ONLY
    else:
        status = ReadinessStatus.NOT_READY
    return RealVisionReadinessReference(
        capture_provider=capture_provider,
        ocr_provider=ocr_provider,
        real_client_tested=real_client_tested,
        map_detection_accuracy=(
            metrics.map_accuracy if metrics.map_accuracy is not None else 0.0
        ),
        entity_detection_accuracy=(
            entity_accuracy if entity_accuracy is not None else 0.0
        ),
        ui_detection_accuracy=(
            metrics.ui_signal_accuracy
            if metrics.ui_signal_accuracy is not None
            else 0.0
        ),
        hp_mp_accuracy=hp_mp_accuracy if hp_mp_accuracy is not None else 0.0,
        quest_state_accuracy=(
            metrics.quest_state_accuracy
            if metrics.quest_state_accuracy is not None
            else 0.0
        ),
        confidence_calibration=(
            calibration if calibration is not None else 0.0
        ),
        sample_count=metrics.sample_count,
        validation_status=status,
    )
