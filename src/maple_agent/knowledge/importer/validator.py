"""Dataset Validation:重复/冲突/缺失引用/非法类型/空字段。"""

from __future__ import annotations

from pydantic import BaseModel, Field

from maple_agent.knowledge.dataset import KnowledgeDataset
from maple_agent.knowledge_graph.models import RelationType


class DatasetValidationResult(BaseModel):
    """校验结果。"""

    valid: bool = True
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)


class DatasetValidator:
    def validate(self, dataset: KnowledgeDataset) -> DatasetValidationResult:
        errors: list[str] = []
        warnings: list[str] = []
        known: dict[str, set[str]] = {}
        entities_by_type = {
            "map": dataset.maps,
            "npc": dataset.npcs,
            "monster": dataset.monsters,
            "item": dataset.items,
        }
        id_field = {
            "map": "map_id",
            "npc": "npc_id",
            "monster": "monster_id",
            "item": "item_id",
        }
        for entity_type, entities in entities_by_type.items():
            ids: set[str] = set()
            names: dict[str, str] = {}
            for entity in entities:
                entity_id = str(getattr(entity, id_field[entity_type]))
                if entity_id in ids:
                    errors.append(f"重复 {entity_type} id: {entity_id}")
                ids.add(entity_id)
                if not entity.name:
                    errors.append(f"{entity_type} 名称为空: {entity_id}")
                if entity.name in names and names[entity.name] != entity_id:
                    warnings.append(
                        f"命名冲突 {entity_type}: {entity.name}"
                    )
                names[entity.name] = entity_id
            known[entity_type] = ids

        relation_types = {item.value for item in RelationType}
        for relation in dataset.relations:
            if relation.relation_type.value not in relation_types:
                errors.append(
                    f"非法关系类型: {relation.relation_type}"
                )
            source_known = known.get(relation.source, set())
            target_known = known.get(relation.target, set())
            if (
                str(relation.source_id) not in source_known
                or str(relation.target_id) not in target_known
            ):
                errors.append(
                    "关系引用缺失: "
                    f"{relation.source}_{relation.source_id} -> "
                    f"{relation.target}_{relation.target_id}"
                )
        return DatasetValidationResult(
            valid=not errors,
            errors=errors,
            warnings=warnings,
        )
