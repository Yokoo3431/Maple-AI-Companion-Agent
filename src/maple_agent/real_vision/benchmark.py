"""RealVisionBenchmark:真实视觉验证指标(无法评估项输出 None,不冒充已测)。"""

from __future__ import annotations

import statistics
from collections.abc import Callable

from maple_agent.real_vision.models import (
    ConfidenceBucket,
    RealVisionBenchmarkResult,
    VisionValidationSample,
)


class RealVisionBenchmark:
    """对样本预测与 ground truth 计算准确率 / 误差 / 延迟。"""

    @staticmethod
    def _bucket(confidence: float) -> str:
        if confidence >= 0.9:
            return "0.9-1.0"
        if confidence >= 0.8:
            return "0.8-0.9"
        if confidence >= 0.7:
            return "0.7-0.8"
        if confidence >= 0.6:
            return "0.6-0.7"
        if confidence >= 0.5:
            return "0.5-0.6"
        return "0.0-0.5"

    def evaluate(
        self,
        samples: list[VisionValidationSample],
        predict_fn: Callable[[VisionValidationSample], dict],
        *,
        capture_latencies_ms: list[float] | None = None,
        ocr_latencies_ms: list[float] | None = None,
        capture_success_rate: float | None = None,
        ocr_success_rate: float | None = None,
    ) -> RealVisionBenchmarkResult:
        reasons: list[str] = []
        total = len(samples)
        map_total = 0
        map_hits = 0
        map_exact = 0
        map_alias = 0
        hp_errors: list[float] = []
        mp_errors: list[float] = []
        npc_hits = npc_pred = npc_gt = 0
        monster_hits = monster_pred = monster_gt = 0
        item_hits = item_pred = item_gt = 0
        quest_total = 0
        quest_hits = 0
        ui_iou_sum = 0.0
        ui_total = 0
        bucket_map: dict[str, list[bool]] = {}
        ocr_ok_count = 0
        for sample in samples:
            gt = sample.ground_truth
            prediction = predict_fn(sample)
            if gt.map_name:
                map_total += 1
                pred_map = prediction.get("visible_map", "")
                if pred_map == gt.map_name:
                    map_hits += 1
                    map_exact += 1
                elif pred_map in gt.aliases:
                    map_hits += 1
                    map_alias += 1
            if gt.hp is not None and prediction.get("hp_reference") is not None:
                hp_errors.append(
                    abs(prediction["hp_reference"] - gt.hp)
                )
            if gt.mp is not None and prediction.get("mp_reference") is not None:
                mp_errors.append(
                    abs(prediction["mp_reference"] - gt.mp)
                )
            pred_entities = prediction.get("visible_entities", [])
            pred_npcs = {
                item.get("name")
                for item in pred_entities
                if item.get("type") == "NPC"
            }
            pred_monsters = {
                item.get("name")
                for item in pred_entities
                if item.get("type") == "MONSTER"
            }
            pred_items = {
                item.get("name")
                for item in pred_entities
                if item.get("type") == "ITEM"
            }
            npc_hits += len(pred_npcs & set(gt.visible_npcs))
            npc_pred += len(pred_npcs)
            npc_gt += len(gt.visible_npcs)
            monster_hits += len(pred_monsters & set(gt.visible_monsters))
            monster_pred += len(pred_monsters)
            monster_gt += len(gt.visible_monsters)
            item_hits += len(pred_items & set(gt.visible_items))
            item_pred += len(pred_items)
            item_gt += len(gt.visible_items)
            if gt.quest_state and prediction.get("quest_state"):
                quest_total += 1
                if prediction["quest_state"] == gt.quest_state:
                    quest_hits += 1
            gt_ui = set(gt.ui_signals)
            pred_ui = set(prediction.get("ui_elements", []))
            if gt_ui or pred_ui:
                ui_total += 1
                union = gt_ui | pred_ui
                intersection = gt_ui & pred_ui
                ui_iou_sum += (
                    len(intersection) / len(union) if union else 1.0
                )
            confidence = prediction.get("confidence")
            if confidence is not None and gt.map_name:
                correct = (
                    prediction.get("visible_map", "") == gt.map_name
                    or prediction.get("visible_map", "")
                    in gt.aliases
                )
                bucket_map.setdefault(self._bucket(confidence), []).append(
                    correct
                )
            if prediction.get("ocr_ok", True):
                ocr_ok_count += 1
        map_accuracy = (
            round(map_hits / map_total, 4) if map_total else None
        )
        map_exact_accuracy = (
            round(map_exact / map_total, 4) if map_total else None
        )
        map_alias_accuracy = (
            round(map_alias / map_total, 4) if map_total else None
        )
        if map_total == 0:
            reasons.append("map accuracy: no ground truth")
        hp_mae = round(sum(hp_errors) / len(hp_errors), 4) if hp_errors else None
        mp_mae = round(sum(mp_errors) / len(mp_errors), 4) if mp_errors else None
        if not hp_errors and not mp_errors:
            reasons.append("hp/mp: no ground truth")
        npc_precision = (
            round(npc_hits / npc_pred, 4) if npc_pred else None
        )
        npc_recall = round(npc_hits / npc_gt, 4) if npc_gt else None
        monster_precision = (
            round(monster_hits / monster_pred, 4) if monster_pred else None
        )
        monster_recall = (
            round(monster_hits / monster_gt, 4) if monster_gt else None
        )
        item_precision = (
            round(item_hits / item_pred, 4) if item_pred else None
        )
        item_recall = round(item_hits / item_gt, 4) if item_gt else None
        quest_state_accuracy = (
            round(quest_hits / quest_total, 4) if quest_total else None
        )
        if quest_total == 0:
            reasons.append("quest state: no ground truth")
        ui_signal_accuracy = (
            round(ui_iou_sum / ui_total, 4) if ui_total else None
        )
        if ui_total == 0:
            reasons.append("ui signals: no ground truth")
        if capture_success_rate is None:
            reasons.append("capture success: not measured")
        if ocr_success_rate is None:
            ocr_success_rate = (
                round(ocr_ok_count / total, 4) if total else None
            )
        buckets = [
            ConfidenceBucket(
                bucket=name,
                sample_count=len(values),
                accuracy=(
                    round(sum(values) / len(values), 4)
                    if values
                    else None
                ),
            )
            for name, values in sorted(bucket_map.items(), reverse=True)
        ]
        if not buckets:
            reasons.append("confidence calibration: no samples")
        return RealVisionBenchmarkResult(
            sample_count=total,
            map_accuracy=map_accuracy,
            map_exact_accuracy=map_exact_accuracy,
            map_alias_accuracy=map_alias_accuracy,
            hp_mae=hp_mae,
            mp_mae=mp_mae,
            npc_precision=npc_precision,
            npc_recall=npc_recall,
            monster_precision=monster_precision,
            monster_recall=monster_recall,
            item_precision=item_precision,
            item_recall=item_recall,
            quest_state_accuracy=quest_state_accuracy,
            ui_signal_accuracy=ui_signal_accuracy,
            capture_success_rate=(
                round(capture_success_rate, 4)
                if capture_success_rate is not None
                else None
            ),
            ocr_success_rate=(
                round(ocr_success_rate, 4)
                if ocr_success_rate is not None
                else None
            ),
            mean_capture_latency_ms=self._mean(capture_latencies_ms),
            p95_capture_latency_ms=self._p95(capture_latencies_ms),
            mean_ocr_latency_ms=self._mean(ocr_latencies_ms),
            confidence_buckets=buckets,
            reasons=reasons,
        )

    @staticmethod
    def _mean(values: list[float] | None) -> float | None:
        if not values:
            return None
        return round(statistics.mean(values), 4)

    @staticmethod
    def _p95(values: list[float] | None) -> float | None:
        if not values:
            return None
        ordered = sorted(values)
        index = max(0, min(len(ordered) - 1, int(0.95 * len(ordered))))
        return round(ordered[index], 4)
