"""Knowledge Acquisition & Quality Gate 数据模型(Phase 13-G,静态知识,只读)。"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class KnowledgeSourceType(StrEnum):
    """知识来源类型。"""

    MANUAL_CURATED = "MANUAL_CURATED"
    LOCAL_STATIC_FILE = "LOCAL_STATIC_FILE"
    STATIC_GAME_RESOURCE = "STATIC_GAME_RESOURCE"
    WIKI_SNAPSHOT = "WIKI_SNAPSHOT"
    COMMUNITY_DATABASE = "COMMUNITY_DATABASE"
    OFFICIAL_PUBLIC_SOURCE = "OFFICIAL_PUBLIC_SOURCE"
    OTHER = "OTHER"


class KnowledgeSourceReference(BaseModel):
    """知识来源 Provenance(时间字段支持固定值,保证确定性)。"""

    source_id: str
    source_type: KnowledgeSourceType
    source_reference: str = ""
    source_name: str = ""
    game_profile: str = ""
    server_profile: str = ""
    data_version: str = ""
    snapshot_version: str = ""
    extracted_at: datetime | None = None
    imported_at: datetime | None = None
    content_hash: str = ""
    license_or_terms_reference: str = ""
    trust_level: float = Field(default=0.5, ge=0, le=1)
    confidence: float = Field(default=0.5, ge=0, le=1)
    adapter_name: str = ""
    adapter_version: str = ""


class KnowledgeDatasetMetadata(BaseModel):
    """Version/provenance metadata for one imported dataset revision."""

    dataset_version: str = ""
    game_profile: str = ""
    server_profile: str = ""
    source_provenance: list[str] = Field(default_factory=list)
    content_hash: str = ""
    adapter_name: str = ""
    adapter_version: str = ""


class CanonicalEntityReference(BaseModel):
    """领域实体 canonical identity(名称不是唯一身份)。"""

    canonical_id: str
    entity_type: str
    display_name: str = ""
    aliases: list[str] = Field(default_factory=list)
    game_profile: str = ""
    server_profile: str = ""
    data_version: str = ""


class MergeOutcome(StrEnum):
    """合并结果。"""

    MERGED = "MERGED"
    DUPLICATE = "DUPLICATE"
    CONFLICT = "CONFLICT"
    UNRESOLVED = "UNRESOLVED"
    REJECTED = "REJECTED"


class MergeRecord(BaseModel):
    """合并审计记录。"""

    external_id: str = ""
    canonical_id: str = ""
    outcome: MergeOutcome
    reason: str = ""
    evidence: dict = Field(default_factory=dict)


class KnowledgeAcquisitionManifest(BaseModel):
    """知识获取 manifest(每次导入生成)。"""

    manifest_id: str
    source_reference: str = ""
    game_profile: str = ""
    server_profile: str = ""
    data_version: str = ""
    entity_counts: dict = Field(default_factory=dict)
    relation_counts: dict = Field(default_factory=dict)
    canonical_mapped_count: int = 0
    unresolved_count: int = 0
    duplicate_count: int = 0
    conflict_count: int = 0
    content_hash: str = ""
    import_status: str = ""
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class KnowledgeCoverageDenominator(BaseModel):
    """覆盖率分母(来源必须明确,否则 coverage 输出 N/A)。"""

    source_name: str = ""
    expected_counts: dict = Field(default_factory=dict)


class KnowledgeQualityBenchmarkResult(BaseModel):
    """知识质量 Benchmark(无法评估项输出 None,不冒充已测)。"""

    total_entities: int = 0
    total_relations: int = 0
    map_count: int = 0
    portal_count: int = 0
    npc_count: int = 0
    monster_count: int = 0
    quest_count: int = 0
    item_count: int = 0
    equipment_count: int = 0
    story_lore_count: int = 0
    entity_coverage: float | None = None
    alias_coverage: float | None = None
    missing_reference_count: int = 0
    missing_reference_rate: float | None = None
    canonical_id_coverage: float | None = None
    provenance_coverage: float | None = None
    profile_binding_coverage: float | None = None
    version_binding_coverage: float | None = None
    unresolved_reference_rate: float | None = None
    dangling_reference_rate: float | None = None
    duplicate_rate: float | None = None
    conflict_rate: float | None = None
    map_topology_valid_rate: float | None = None
    portal_target_valid_rate: float | None = None
    source_validation_rate: float | None = None
    validation_score: float | None = None
    reasons: list[str] = Field(default_factory=list)


class KnowledgeReadinessPolicy(BaseModel):
    """知识就绪阈值(集中配置,禁止散落 magic number)。"""

    minimum_total_entities: int = Field(default=20, ge=0)
    minimum_canonical_id_coverage: float = Field(default=0.9, ge=0, le=1)
    minimum_provenance_coverage: float = Field(default=0.9, ge=0, le=1)
    minimum_profile_version_binding: float = Field(
        default=0.9,
        ge=0,
        le=1,
    )
    maximum_dangling_rate: float = Field(default=0.02, ge=0, le=1)
    maximum_unresolved_rate: float = Field(default=0.02, ge=0, le=1)
    maximum_conflict_rate: float = Field(default=0.0, ge=0, le=1)
    minimum_validation_score: float = Field(default=0.9, ge=0, le=1)
    required_source_count: int = Field(default=1, ge=0)
    coverage_denominator_required: bool = True

    @classmethod
    def from_dict(
        cls,
        data: dict | None,
    ) -> KnowledgeReadinessPolicy:
        if not data:
            return cls()
        fields = set(cls.model_fields)
        return cls(
            **{
                key: value
                for key, value in data.items()
                if key in fields
            }
        )

    def to_dict(self) -> dict:
        return self.model_dump(mode="json")
