"""Versioned real knowledge dataset package loading and validation."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from maple_agent.knowledge.importer.builder import build_dataset
from maple_agent.knowledge.importer.validator import DatasetValidator
from maple_agent.knowledge_graph.validation import validate_relation_records
from maple_agent.knowledge_quality.models import (
    CanonicalEntityReference,
    KnowledgeCoverageDenominator,
    KnowledgeSourceReference,
    KnowledgeSourceType,
)
from maple_agent.knowledge_quality.source import content_hash

PACKAGE_SCHEMA_VERSION = "1.0"
ENTITY_FILES = (
    "maps",
    "npcs",
    "monsters",
    "items",
    "equipment",
    "quests",
    "story_lore",
    "relations",
)
ENTITY_ID_FIELDS = {
    "maps": "map_id",
    "npcs": "npc_id",
    "monsters": "monster_id",
    "items": "item_id",
    "equipment": "equipment_id",
    "quests": "quest_id",
    "story_lore": "lore_id",
}
REQUIRED_PROVENANCE_FIELDS = (
    "source_id",
    "source_type",
    "game_profile",
    "server_profile",
    "data_version",
)


class KnowledgeDatasetPackageManifest(BaseModel):
    """Auditable metadata for one static source snapshot."""

    schema_version: str = PACKAGE_SCHEMA_VERSION
    dataset_version: str
    source_id: str
    source_name: str
    source_type: KnowledgeSourceType
    source_reference: str
    game_profile: str
    server_profile: str
    snapshot_version: str
    content_hash: str
    entity_counts: dict[str, int] = Field(default_factory=dict)
    relation_counts: dict[str, int] = Field(default_factory=dict)
    expected_counts: dict[str, int] = Field(default_factory=dict)
    provenance_fields: list[str] = Field(
        default_factory=lambda: list(REQUIRED_PROVENANCE_FIELDS)
    )
    license_or_terms_reference: str = ""
    sanitized: bool = True


class DatasetPackageValidation(BaseModel):
    """Deterministic package validation report."""

    valid: bool
    actual_counts: dict[str, int] = Field(default_factory=dict)
    expected_counts: dict[str, int] = Field(default_factory=dict)
    coverage: dict[str, float | None] = Field(default_factory=dict)
    provenance_coverage: float | None = None
    duplicate_id_count: int = 0
    alias_conflict_count: int = 0
    missing_reference_count: int = 0
    invalid_relation_count: int = 0
    relation_count: int = 0
    duplicate_edge_count: int = 0
    dangling_relation_count: int = 0
    invalid_entity_type_count: int = 0
    invalid_relation_type_count: int = 0
    invalid_relation_endpoint_count: int = 0
    missing_relation_provenance_count: int = 0
    invalid_relation_confidence_count: int = 0
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


@dataclass(frozen=True)
class KnowledgeDatasetPackage:
    """A local, sanitized, versioned packet plus its canonical index."""

    directory: Path
    manifest: KnowledgeDatasetPackageManifest
    packet: dict[str, list[dict[str, Any]]]
    canonical_entities: list[CanonicalEntityReference]

    @classmethod
    def load(cls, directory: str | Path) -> KnowledgeDatasetPackage:
        package_dir = Path(directory)
        manifest = KnowledgeDatasetPackageManifest.model_validate(
            json.loads((package_dir / "manifest.json").read_text(encoding="utf-8"))
        )
        entities_dir = package_dir / "entities"
        packet: dict[str, list[dict[str, Any]]] = {}
        for entity_type in ENTITY_FILES:
            path = entities_dir / f"{entity_type}.json"
            if not path.exists():
                packet[entity_type] = []
                continue
            value = json.loads(path.read_text(encoding="utf-8"))
            if not isinstance(value, list):
                raise ValueError(f"entity file must contain a list: {path}")
            packet[entity_type] = value
        canonical_path = package_dir / "canonical_entities.json"
        canonical_raw = (
            json.loads(canonical_path.read_text(encoding="utf-8"))
            if canonical_path.exists()
            else []
        )
        canonical_entities = [
            CanonicalEntityReference.model_validate(item)
            for item in canonical_raw
        ]
        return cls(
            directory=package_dir,
            manifest=manifest,
            packet=packet,
            canonical_entities=canonical_entities,
        )

    def source_reference(self) -> KnowledgeSourceReference:
        """Return the local package source with its public source type."""
        return KnowledgeSourceReference(
            source_id=self.manifest.source_id,
            source_type=self.manifest.source_type,
            source_reference=str(self.directory),
            source_name=self.manifest.source_name,
            game_profile=self.manifest.game_profile,
            server_profile=self.manifest.server_profile,
            data_version=self.manifest.dataset_version,
            snapshot_version=self.manifest.snapshot_version,
            license_or_terms_reference=self.manifest.license_or_terms_reference,
        )

    def denominator(self) -> KnowledgeCoverageDenominator:
        key_map = {
            "maps": "map",
            "npcs": "npc",
            "monsters": "monster",
            "items": "item",
            "equipment": "equipment",
            "quests": "quest",
            "story_lore": "story_lore",
        }
        return KnowledgeCoverageDenominator(
            source_name=self.manifest.source_id,
            expected_counts={
                key_map.get(key, key): value
                for key, value in self.manifest.expected_counts.items()
            },
        )

    def canonical_mapper_entities(self) -> list[CanonicalEntityReference]:
        return list(self.canonical_entities)

    def canonical_source_id_mapping(self) -> dict[str, str]:
        """Return deterministic source-ID mappings for the existing mapper."""
        mapping: dict[str, str] = {}
        for entity_type, id_field in ENTITY_ID_FIELDS.items():
            canonical_type = entity_type.rstrip("s")
            for item in self.packet.get(entity_type, []):
                external_id = str(item.get(id_field, ""))
                if external_id:
                    mapping[external_id] = f"{canonical_type}_{external_id}"
        return mapping

    def validate(self) -> DatasetPackageValidation:
        errors: list[str] = []
        warnings: list[str] = []
        actual_counts = {
            key: len(self.packet.get(key, []))
            for key in ENTITY_FILES
            if key != "relations"
        }
        actual_relation_counts = dict(
            Counter(
                str(relation.get("relation_type", "")).upper()
                for relation in self.packet.get("relations", [])
            )
        )
        expected_counts = dict(self.manifest.expected_counts)
        coverage = {
            key: (
                round(actual_counts.get(key, 0) / expected, 4)
                if expected
                else None
            )
            for key, expected in expected_counts.items()
        }
        for key, expected in expected_counts.items():
            if actual_counts.get(key, 0) < expected:
                warnings.append(
                    f"{key} coverage below denominator: "
                    f"{actual_counts.get(key, 0)}/{expected}"
                )
        if self.manifest.schema_version != PACKAGE_SCHEMA_VERSION:
            errors.append(
                f"unsupported package schema: {self.manifest.schema_version}"
            )
        if not self.manifest.sanitized:
            errors.append("package is not marked sanitized")
        if self.manifest.entity_counts != actual_counts:
            errors.append("manifest entity_counts do not match package files")
        if self.manifest.relation_counts and (
            self.manifest.relation_counts != actual_relation_counts
        ):
            errors.append("manifest relation_counts do not match package relations")
        if self.manifest.content_hash != content_hash(self.packet):
            errors.append("manifest content_hash does not match package files")

        duplicate_id_count = 0
        alias_conflict_count = 0
        provenance_total = 0
        provenance_complete = 0
        known_ids: dict[str, set[str]] = {
            entity_type: {
                str(item.get(id_field, ""))
                for item in self.packet.get(entity_type, [])
            }
            for entity_type, id_field in ENTITY_ID_FIELDS.items()
        }
        relation_known_ids = {
            "map": known_ids["maps"],
            "npc": known_ids["npcs"],
            "monster": known_ids["monsters"],
            "item": known_ids["items"],
            "equipment": known_ids["equipment"],
            "quest": known_ids["quests"],
            "story_lore": known_ids["story_lore"],
        }
        for entity_type, id_field in ENTITY_ID_FIELDS.items():
            seen_ids: set[str] = set()
            aliases: dict[str, str] = {}
            for item in self.packet.get(entity_type, []):
                entity_id = str(item.get(id_field, ""))
                if entity_id in seen_ids:
                    duplicate_id_count += 1
                seen_ids.add(entity_id)
                provenance_total += 1
                provenance = item.get("provenance") or {}
                if all(provenance.get(field) for field in self.manifest.provenance_fields):
                    provenance_complete += 1
                names = [str(item.get("name", "")), *item.get("aliases", [])]
                for name in names:
                    normalized = "".join(name.lower().split())
                    if not normalized:
                        continue
                    previous = aliases.get(normalized)
                    if previous is not None and previous != entity_id:
                        alias_conflict_count += 1
                    aliases[normalized] = entity_id
        if duplicate_id_count:
            errors.append(f"duplicate entity IDs: {duplicate_id_count}")
        if alias_conflict_count:
            errors.append(f"alias conflicts: {alias_conflict_count}")
        provenance_coverage = (
            round(provenance_complete / provenance_total, 4)
            if provenance_total
            else None
        )
        if provenance_coverage != 1.0:
            errors.append("provenance completeness below 1.0")

        missing_reference_count = 0
        for quest in self.packet.get("quests", []):
            for field, target_type in (
                ("npc_ids", "npcs"),
                ("map_ids", "maps"),
                ("item_ids", "items"),
                ("monster_ids", "monsters"),
            ):
                for target_id in quest.get(field, []) or []:
                    if str(target_id) not in known_ids[target_type]:
                        missing_reference_count += 1
        for npc in self.packet.get("npcs", []):
            map_id = npc.get("map_id")
            if map_id is not None and str(map_id) not in known_ids["maps"]:
                missing_reference_count += 1
        if missing_reference_count:
            warnings.append(
                "bounded snapshot missing references: "
                f"{missing_reference_count} (partial package warning)"
            )

        relation_validation = validate_relation_records(
            self.packet.get("relations", []),
            relation_known_ids,
        )
        if not relation_validation.valid:
            errors.extend(relation_validation.errors)

        dataset, import_result = build_dataset(
            self.packet,
            source=self.manifest.source_id,
            version=self.manifest.dataset_version,
        )
        dataset_validation = DatasetValidator().validate(dataset)
        importer_missing_reference_count = sum(
            1
            for message in [*import_result.warnings, *dataset_validation.errors]
            if "关系引用缺失" in message or "dangling" in message.lower()
        )
        invalid_relation_count = sum(
            1
            for message in [*import_result.warnings, *dataset_validation.errors]
            if "非法关系" in message or "invalid relation" in message.lower()
        )
        invalid_relation_count = max(
            invalid_relation_count,
            relation_validation.invalid_relation_type_count
            + relation_validation.invalid_endpoint_count,
        )
        if invalid_relation_count:
            errors.append(f"invalid relations: {invalid_relation_count}")
        errors.extend(dataset_validation.errors)
        warnings.extend(import_result.warnings)
        return DatasetPackageValidation(
            valid=not errors,
            actual_counts=actual_counts,
            expected_counts=expected_counts,
            coverage=coverage,
            provenance_coverage=provenance_coverage,
            duplicate_id_count=duplicate_id_count,
            alias_conflict_count=alias_conflict_count,
            missing_reference_count=max(
                missing_reference_count,
                importer_missing_reference_count,
                relation_validation.dangling_reference_count,
            ),
            invalid_relation_count=invalid_relation_count,
            relation_count=relation_validation.edge_count,
            duplicate_edge_count=relation_validation.duplicate_edge_count,
            dangling_relation_count=relation_validation.dangling_reference_count,
            invalid_entity_type_count=relation_validation.invalid_entity_type_count,
            invalid_relation_type_count=relation_validation.invalid_relation_type_count,
            invalid_relation_endpoint_count=relation_validation.invalid_endpoint_count,
            missing_relation_provenance_count=relation_validation.missing_provenance_count,
            invalid_relation_confidence_count=relation_validation.invalid_confidence_count,
            errors=list(dict.fromkeys(errors)),
            warnings=list(dict.fromkeys(warnings)),
        )


class KnowledgeDatasetPackageAdapter:
    """Existing source adapter contract for a local package directory."""

    adapter_name = "KnowledgeDatasetPackageAdapter"
    adapter_version = "1.0"

    def __init__(self) -> None:
        self.last_package: KnowledgeDatasetPackage | None = None
        self.last_validation: DatasetPackageValidation | None = None

    def load(self, source: KnowledgeSourceReference) -> dict:
        package = KnowledgeDatasetPackage.load(source.source_reference)
        validation = package.validate()
        if not validation.valid:
            raise ValueError(
                "invalid knowledge dataset package: "
                + "; ".join(validation.errors)
            )
        self.last_package = package
        self.last_validation = validation
        return package.packet
