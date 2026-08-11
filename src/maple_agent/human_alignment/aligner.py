"""HumanAlignmentAligner:偏好/历史/反馈 -> 对齐决策参考(只读)。"""

from __future__ import annotations

import json
from pathlib import Path

from maple_agent.architecture import TRACE_SCHEMA_VERSION
from maple_agent.decision_reference.models import DecisionReference
from maple_agent.human_alignment.feedback import FeedbackProcessor
from maple_agent.human_alignment.models import (
    AlignmentScore,
    HumanAlignedDecisionReference,
    HumanFeedback,
)
from maple_agent.human_alignment.preference import PreferenceMemory


class HumanAlignmentAligner:
    """结合用户偏好与反馈优化决策参考。"""

    def __init__(
        self,
        *,
        memory: PreferenceMemory | None = None,
        feedback_processor: FeedbackProcessor | None = None,
    ) -> None:
        self.memory = memory or PreferenceMemory()
        self.feedback_processor = (
            feedback_processor or FeedbackProcessor(self.memory)
        )
        self.last_reference: HumanAlignedDecisionReference | None = None
        self.last_score: AlignmentScore | None = None

    def align(
        self,
        *,
        decision_reference: DecisionReference,
        feedback: HumanFeedback | None = None,
    ) -> HumanAlignedDecisionReference:
        if feedback is not None:
            self.feedback_processor.process(feedback=feedback)
        preferred, rejected = self._apply_memory(decision_reference)
        alignment = self._score(decision_reference)
        self.last_score = alignment
        adjustments = self._adjustments(preferred, rejected)
        reasoning = self._reasoning(preferred, rejected, alignment)
        reference = HumanAlignedDecisionReference(
            preferred_options=preferred,
            rejected_options=rejected,
            alignment_score=alignment.alignment_score,
            adjustments=adjustments,
            reasoning=reasoning,
        )
        self.last_reference = reference
        return reference

    def _apply_memory(
        self,
        decision_reference: DecisionReference,
    ) -> tuple[list, list[str]]:
        accepted = set(self.memory.accepted_option_ids())
        rejected = set(self.memory.rejected_option_ids())
        preferred: list = []
        placed: set[str] = set()
        for option in decision_reference.recommended_options:
            if option.option_id in rejected:
                continue
            preferred.append(option)
            placed.add(option.option_id)
        for option in decision_reference.alternative_options:
            if (
                option.option_id in accepted
                and option.option_id not in placed
            ):
                preferred.append(option)
                placed.add(option.option_id)
        preferred.sort(
            key=lambda option: (
                option.option_id in accepted,
                option.confidence,
            ),
            reverse=True,
        )
        return preferred, sorted(rejected)

    def _score(
        self,
        decision_reference: DecisionReference,
    ) -> AlignmentScore:
        preference_match = self._preference_match(decision_reference)
        historical_approval = self.memory.approval_rate()
        decision_quality = decision_reference.confidence
        risk_compatibility = {
            "LOW": 1.0,
            "MEDIUM": 0.7,
            "HIGH": 0.3,
        }.get(decision_reference.risk_level, 0.5)
        alignment_score = round(
            0.4 * preference_match
            + 0.3 * historical_approval
            + 0.2 * decision_quality
            + 0.1 * risk_compatibility,
            4,
        )
        return AlignmentScore(
            alignment_score=alignment_score,
            preference_match=preference_match,
            historical_approval=historical_approval,
            decision_quality=decision_quality,
            risk_compatibility=risk_compatibility,
            components={
                "preference_match": preference_match,
                "historical_approval": historical_approval,
                "decision_quality": decision_quality,
                "risk_compatibility": risk_compatibility,
            },
        )

    def _preference_match(
        self,
        decision_reference: DecisionReference,
    ) -> float:
        accepted = set(self.memory.accepted_option_ids())
        recommended_ids = {
            option.option_id
            for option in decision_reference.recommended_options
        }
        if not recommended_ids:
            return 0.5
        hits = len(recommended_ids & accepted)
        return round(hits / len(recommended_ids), 4)

    @staticmethod
    def _adjustments(
        preferred: list,
        rejected: list[str],
    ) -> list[str]:
        adjustments: list[str] = []
        if rejected:
            adjustments.append(
                "已移除用户拒绝选项: " + ", ".join(rejected)
            )
        if preferred:
            adjustments.append(
                f"保留 {len(preferred)} 个首选选项"
            )
        return adjustments

    @staticmethod
    def _reasoning(
        preferred: list,
        rejected: list[str],
        alignment: AlignmentScore,
    ) -> list[str]:
        reasoning: list[str] = []
        if preferred:
            reasoning.append(
                "首选: " + ", ".join(option.option_id for option in preferred)
            )
        if rejected:
            reasoning.append("拒绝: " + ", ".join(rejected))
        reasoning.append(f"对齐评分: {alignment.alignment_score:.2f}")
        return reasoning


def save_human_alignment_trace(
    sessions_dir: str | Path,
    trace_id: str,
    *,
    decision_reference: DecisionReference,
    feedback: HumanFeedback | None,
    alignment: AlignmentScore,
) -> None:
    """写入 human_alignment_trace.json(统一 Replay)。"""
    directory = Path(sessions_dir) / trace_id
    directory.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": TRACE_SCHEMA_VERSION,
        "decision_reference": decision_reference.model_dump(mode="json"),
        "feedback": (
            feedback.model_dump(mode="json")
            if feedback is not None
            else {}
        ),
        "alignment": alignment.model_dump(mode="json"),
    }
    (directory / "human_alignment_trace.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
