"""Knowledge Readiness:由 Benchmark 自动生成(禁止手工 READY)。"""

from __future__ import annotations

from maple_agent.knowledge_quality.models import (
    KnowledgeCoverageDenominator,
    KnowledgeQualityBenchmarkResult,
    KnowledgeReadinessPolicy,
)
from maple_agent.safety_vnext.models import (
    KnowledgeReadinessReference,
    ReadinessStatus,
)


def build_knowledge_readiness(
    benchmark: KnowledgeQualityBenchmarkResult,
    *,
    policy: KnowledgeReadinessPolicy | None = None,
    game_profile: str = "",
    server_version: str = "",
    dataset_version: str = "",
    source_provenance: str = "",
    denominators: list[KnowledgeCoverageDenominator] | None = None,
) -> KnowledgeReadinessReference:
    """按集中阈值自动判定;denominator 缺失或阈值未达标均不得 READY。"""
    policy = policy or KnowledgeReadinessPolicy()
    reasons: list[str] = list(benchmark.reasons)
    if benchmark.total_entities < policy.minimum_total_entities:
        reasons.append(
            f"insufficient entities: {benchmark.total_entities} "
            f"< {policy.minimum_total_entities}"
        )
    if (
        benchmark.canonical_id_coverage is not None
        and benchmark.canonical_id_coverage
        < policy.minimum_canonical_id_coverage
    ):
        reasons.append("canonical id coverage below threshold")
    if (
        benchmark.provenance_coverage is not None
        and benchmark.provenance_coverage
        < policy.minimum_provenance_coverage
    ):
        reasons.append("provenance coverage below threshold")
    binding_values = [
        value
        for value in (
            benchmark.profile_binding_coverage,
            benchmark.version_binding_coverage,
        )
        if value is not None
    ]
    binding = (
        round(sum(binding_values) / len(binding_values), 4)
        if binding_values
        else None
    )
    if binding is not None and binding < policy.minimum_profile_version_binding:
        reasons.append("profile/version binding below threshold")
    if (
        benchmark.dangling_reference_rate is not None
        and benchmark.dangling_reference_rate > policy.maximum_dangling_rate
    ):
        reasons.append("dangling rate above threshold")
    if (
        benchmark.unresolved_reference_rate is not None
        and benchmark.unresolved_reference_rate
        > policy.maximum_unresolved_rate
    ):
        reasons.append("unresolved rate above threshold")
    if (
        benchmark.conflict_rate is not None
        and benchmark.conflict_rate > policy.maximum_conflict_rate
    ):
        reasons.append("conflict rate above threshold")
    if (
        benchmark.validation_score is not None
        and benchmark.validation_score < policy.minimum_validation_score
    ):
        reasons.append("validation score below threshold")
    if not denominators and policy.coverage_denominator_required:
        reasons.append("coverage denominator missing")
    if not game_profile or not server_version:
        reasons.append("profile/version missing")
    has_entities = benchmark.total_entities > 0
    passed = (
        has_entities
        and benchmark.total_entities >= policy.minimum_total_entities
        and benchmark.canonical_id_coverage is not None
        and benchmark.canonical_id_coverage
        >= policy.minimum_canonical_id_coverage
        and benchmark.provenance_coverage is not None
        and benchmark.provenance_coverage
        >= policy.minimum_provenance_coverage
        and binding is not None
        and binding >= policy.minimum_profile_version_binding
        and benchmark.dangling_reference_rate is not None
        and benchmark.dangling_reference_rate <= policy.maximum_dangling_rate
        and benchmark.unresolved_reference_rate is not None
        and benchmark.unresolved_reference_rate
        <= policy.maximum_unresolved_rate
        and benchmark.conflict_rate is not None
        and benchmark.conflict_rate <= policy.maximum_conflict_rate
        and benchmark.validation_score is not None
        and benchmark.validation_score >= policy.minimum_validation_score
        and bool(denominators or not policy.coverage_denominator_required)
        and bool(game_profile and server_version)
    )
    if passed:
        status = ReadinessStatus.READY
    elif has_entities:
        status = ReadinessStatus.FOUNDATION_ONLY
    else:
        status = ReadinessStatus.NOT_READY
    coverage = _coverage(benchmark, denominators)
    return KnowledgeReadinessReference(
        game_profile=game_profile,
        server_version=server_version,
        dataset_version=dataset_version,
        source_provenance=source_provenance,
        map_coverage=coverage.get("map"),
        portal_coverage=coverage.get("portal"),
        npc_coverage=coverage.get("npc"),
        monster_coverage=coverage.get("monster"),
        quest_coverage=coverage.get("quest"),
        item_coverage=coverage.get("item"),
        validation_score=(
            benchmark.validation_score
            if benchmark.validation_score is not None
            else 0.0
        ),
        status=status,
    )


def _coverage(
    benchmark: KnowledgeQualityBenchmarkResult,
    denominators: list[KnowledgeCoverageDenominator] | None,
) -> dict[str, float]:
    """coverage = validated / expected;denominator 缺失 -> N/A(0.0 但 reasons 已说明)。"""
    if not denominators:
        return {
            "map": 0.0,
            "portal": 0.0,
            "npc": 0.0,
            "monster": 0.0,
            "quest": 0.0,
            "item": 0.0,
        }
    expected: dict[str, int] = {}
    for denominator in denominators:
        for key, value in denominator.expected_counts.items():
            expected[key] = max(expected.get(key, 0), int(value))
    actual = {
        "map": benchmark.map_count,
        "portal": benchmark.portal_count,
        "npc": benchmark.npc_count,
        "monster": benchmark.monster_count,
        "quest": benchmark.quest_count,
        "item": benchmark.item_count,
    }
    coverage: dict[str, float] = {}
    for key, count in actual.items():
        expected_count = expected.get(key, 0)
        coverage[key] = (
            round(count / expected_count, 4) if expected_count else 0.0
        )
    return coverage
