"""MapleCognitiveContextBuilder:认知上下文聚合(只读)。"""

from __future__ import annotations

from maple_agent.decision_reference.models import DecisionReference
from maple_agent.failure_intelligence.models import (
    FailurePreventionReference,
)
from maple_agent.human_alignment.models import HumanAlignedDecisionReference
from maple_agent.maple_context.models import MapleCognitiveContext
from maple_agent.memory_association.models import SemanticMemoryReference
from maple_agent.memory_graph.models import RelevantMemoryReference


class MapleCognitiveContextBuilder:
    """聚合决策 / 对齐 / 记忆 / 语义关联 / 失败智能。"""

    def build(
        self,
        *,
        decision_reference: DecisionReference | None = None,
        human_alignment: HumanAlignedDecisionReference | None = None,
        memory_reference: RelevantMemoryReference | None = None,
        semantic_memory_reference: SemanticMemoryReference | None = None,
        failure_reference: FailurePreventionReference | None = None,
    ) -> MapleCognitiveContext:
        confidence = self._confidence(
            decision_reference,
            human_alignment,
            memory_reference,
            semantic_memory_reference,
        )
        return MapleCognitiveContext(
            decision_reference=self._decision_text(decision_reference),
            human_alignment_reference=(
                f"{human_alignment.alignment_score:.2f}"
                if human_alignment is not None
                else ""
            ),
            memory_reference=(
                f"{memory_reference.confidence:.2f}"
                if memory_reference is not None
                else ""
            ),
            semantic_memory_reference=(
                f"{semantic_memory_reference.confidence:.2f}"
                if semantic_memory_reference is not None
                else ""
            ),
            failure_reference=(
                failure_reference.summary
                if failure_reference is not None
                else ""
            ),
            confidence=confidence,
        )

    @staticmethod
    def _decision_text(
        decision_reference: DecisionReference | None,
    ) -> str:
        if decision_reference is None:
            return ""
        return ", ".join(
            option.option_id
            for option in decision_reference.recommended_options
        )

    @staticmethod
    def _confidence(
        decision_reference: DecisionReference | None,
        human_alignment: HumanAlignedDecisionReference | None,
        memory_reference: RelevantMemoryReference | None,
        semantic_memory_reference: SemanticMemoryReference | None,
    ) -> float:
        values: list[float] = []
        if decision_reference is not None:
            values.append(decision_reference.confidence)
        if human_alignment is not None:
            values.append(human_alignment.alignment_score)
        if memory_reference is not None:
            values.append(memory_reference.confidence)
        if semantic_memory_reference is not None:
            values.append(semantic_memory_reference.confidence)
        if not values:
            return 0.0
        return round(sum(values) / len(values), 4)
