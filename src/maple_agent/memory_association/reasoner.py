"""AssociationReasoner:语义关联摘要与参考(只读)。"""

from __future__ import annotations

from maple_agent.memory_association.models import (
    SemanticAssociationSummary,
    SemanticMemoryReference,
    SemanticMemoryRelation,
    SemanticRelationType,
)


class AssociationReasoner:
    """把语义关系聚合为摘要与参考。"""

    @staticmethod
    def summarize(
        relations: list[SemanticMemoryRelation],
    ) -> SemanticAssociationSummary:
        strong = [
            relation
            for relation in relations
            if relation.confidence >= 0.7
        ]
        risk = [
            relation.reasoning
            for relation in relations
            if relation.relation_type
            in (
                SemanticRelationType.FAILURE_PATTERN,
                SemanticRelationType.CAUSAL_LINK,
            )
        ]
        success = [
            relation.reasoning
            for relation in relations
            if relation.relation_type
            is SemanticRelationType.SUCCESS_PATTERN
        ]
        preference = [
            relation.reasoning
            for relation in relations
            if relation.relation_type
            is SemanticRelationType.PREFERENCE_ALIGNMENT
        ]
        hints = [
            relation.reasoning
            for relation in relations
            if relation.relation_type
            is SemanticRelationType.DECISION_IMPROVEMENT
        ]
        confidence = (
            round(
                sum(relation.confidence for relation in relations)
                / len(relations),
                4,
            )
            if relations
            else 0.0
        )
        return SemanticAssociationSummary(
            strong_relations=len(strong),
            risk_patterns=risk,
            successful_patterns=success,
            preference_patterns=preference,
            improvement_hints=hints,
            confidence=confidence,
        )

    @staticmethod
    def build_reference(
        relations: list[SemanticMemoryRelation],
    ) -> SemanticMemoryReference:
        related: list[str] = []
        failures: list[str] = []
        hints: list[str] = []
        preference: list[str] = []
        world: list[str] = []
        for relation in relations:
            if relation.relation_type in (
                SemanticRelationType.GOAL_SIMILARITY,
                SemanticRelationType.SUCCESS_PATTERN,
            ):
                related.append(relation.target_memory)
            if relation.relation_type is SemanticRelationType.FAILURE_PATTERN:
                related.append(relation.target_memory)
                failures.append(relation.source_memory)
            elif (
                relation.relation_type
                is SemanticRelationType.DECISION_IMPROVEMENT
            ):
                hints.append(relation.target_memory)
            elif (
                relation.relation_type
                is SemanticRelationType.PREFERENCE_ALIGNMENT
            ):
                preference.append(relation.target_memory)
            elif relation.relation_type is SemanticRelationType.WORLD_CONTEXT:
                world.append(relation.target_memory)
        confidence = (
            round(
                sum(relation.confidence for relation in relations)
                / len(relations),
                4,
            )
            if relations
            else 0.0
        )
        return SemanticMemoryReference(
            related_experiences=sorted(set(related)),
            failure_patterns=sorted(set(failures)),
            decision_hints=sorted(set(hints)),
            preference_alignment=sorted(set(preference)),
            world_context=sorted(set(world)),
            confidence=confidence,
        )
