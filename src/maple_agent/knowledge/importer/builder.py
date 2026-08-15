"""Dataset Builder:外部结构化数据 → KnowledgeDataset。"""

from __future__ import annotations

from maple_agent.knowledge.dataset import KnowledgeDataset
from maple_agent.knowledge.importer.models import ImportResult
from maple_agent.knowledge.importer.normalizer import (
    normalize_alias,
    normalize_name,
    normalize_relation,
)
from maple_agent.knowledge_graph.models import (
    EquipmentNode,
    ItemNode,
    KnowledgeEntityProvenance,
    MapNode,
    MonsterNode,
    NPCNode,
    QuestNode,
    Relation,
    RelationType,
    StoryLoreNode,
)


def build_dataset(
    source_data: dict,
    *,
    source: str = "external",
    version: str = "v1",
) -> tuple[KnowledgeDataset, ImportResult]:
    """把外部结构化数据转换为数据集;收集重复/缺失引用/非法关系警告。"""
    warnings: list[str] = []
    maps: list[MapNode] = []
    npcs: list[NPCNode] = []
    monsters: list[MonsterNode] = []
    items: list[ItemNode] = []
    equipment: list[EquipmentNode] = []
    quests: list[QuestNode] = []
    story_lore: list[StoryLoreNode] = []
    relations: list[Relation] = []

    seen_ids: dict[str, set[str]] = {
        "map": set(),
        "npc": set(),
        "monster": set(),
        "item": set(),
        "equipment": set(),
        "quest": set(),
        "story_lore": set(),
    }
    seen_names: dict[str, dict[str, str]] = {
        "map": {},
        "npc": {},
        "monster": {},
        "item": {},
        "equipment": {},
        "quest": {},
        "story_lore": {},
    }

    def provenance(item: dict) -> KnowledgeEntityProvenance:
        data = {
            "source_id": source,
            "source_type": "IMPORT",
            "data_version": version,
        }
        data.update(item.get("provenance", {}) or {})
        return KnowledgeEntityProvenance.model_validate(data)

    def add_entity(entity_type: str, entity_id, name: str, node) -> None:
        key = str(entity_id)
        if key in seen_ids[entity_type]:
            warnings.append(f"重复 {entity_type} id: {key}(已跳过)")
            return
        if not name:
            warnings.append(f"{entity_type} 名称为空(已跳过): {key}")
            return
        if name in seen_names[entity_type] and seen_names[entity_type][name] != key:
            warnings.append(f"命名冲突 {entity_type}: {name}(保留首个)")
            return
        seen_ids[entity_type].add(key)
        seen_names[entity_type][name] = key
        nodes = {
            "map": maps,
            "npc": npcs,
            "monster": monsters,
            "item": items,
            "equipment": equipment,
            "quest": quests,
            "story_lore": story_lore,
        }[entity_type]
        nodes.append(node)

    for item in source_data.get("maps", []):
        node = MapNode(
            map_id=item.get("map_id"),
            name=normalize_name(item.get("name", "")),
            aliases=normalize_alias(item.get("aliases", [])),
            region=normalize_name(item.get("region", "")),
            parent_region=normalize_name(item.get("parent_region", "")),
            connections=[
                connection
                for connection in item.get("connections", [])
                if connection is not None
            ],
            provenance=provenance(item),
            confidence=item.get("confidence", 0.0),
            version=item.get("version", version),
        )
        add_entity("map", node.map_id, node.name, node)
    for item in source_data.get("npcs", []):
        node = NPCNode(
            npc_id=item.get("npc_id"),
            name=normalize_name(item.get("name", "")),
            aliases=normalize_alias(item.get("aliases", [])),
            location=item.get("map_id"),
            description=normalize_name(item.get("description", "")),
            provenance=provenance(item),
            confidence=item.get("confidence", 0.0),
            version=item.get("version", version),
        )
        add_entity("npc", node.npc_id, node.name, node)
    for item in source_data.get("monsters", []):
        node = MonsterNode(
            monster_id=item.get("monster_id"),
            name=normalize_name(item.get("name", "")),
            aliases=normalize_alias(item.get("aliases", [])),
            location=item.get("map_id"),
            level=item.get("level"),
            drops=[drop for drop in item.get("drops", []) if drop is not None],
            provenance=provenance(item),
            confidence=item.get("confidence", 0.0),
            version=item.get("version", version),
        )
        add_entity("monster", node.monster_id, node.name, node)
    for item in source_data.get("items", []):
        node = ItemNode(
            item_id=item.get("item_id"),
            name=normalize_name(item.get("name", "")),
            aliases=normalize_alias(item.get("aliases", [])),
            provenance=provenance(item),
            confidence=item.get("confidence", 0.0),
            version=item.get("version", version),
        )
        add_entity("item", node.item_id, node.name, node)

    for item in source_data.get("equipment", []):
        node = EquipmentNode(
            equipment_id=item.get("equipment_id"),
            name=normalize_name(item.get("name", "")),
            aliases=normalize_alias(item.get("aliases", [])),
            slot=normalize_name(item.get("slot", "")),
            level=item.get("level"),
            attributes=item.get("attributes", {}) or {},
            provenance=provenance(item),
            confidence=item.get("confidence", 0.0),
            version=item.get("version", version),
        )
        add_entity("equipment", node.equipment_id, node.name, node)

    for item in source_data.get("quests", []):
        node = QuestNode(
            quest_id=item.get("quest_id"),
            name=normalize_name(item.get("name", "")),
            aliases=normalize_alias(item.get("aliases", [])),
            description=normalize_name(item.get("description", "")),
            npc_ids=[value for value in item.get("npc_ids", []) if value is not None],
            map_ids=[value for value in item.get("map_ids", []) if value is not None],
            item_ids=[value for value in item.get("item_ids", []) if value is not None],
            monster_ids=[
                value for value in item.get("monster_ids", []) if value is not None
            ],
            provenance=provenance(item),
            confidence=item.get("confidence", 0.0),
            version=item.get("version", version),
        )
        add_entity("quest", node.quest_id, node.name, node)

    for item in source_data.get("story_lore", []):
        node = StoryLoreNode(
            lore_id=item.get("lore_id"),
            name=normalize_name(item.get("name", "")),
            aliases=normalize_alias(item.get("aliases", [])),
            description=normalize_name(item.get("description", "")),
            topic=normalize_name(item.get("topic", "")),
            provenance=provenance(item),
            confidence=item.get("confidence", 0.0),
            version=item.get("version", version),
        )
        add_entity("story_lore", node.lore_id, node.name, node)

    for item in source_data.get("relations", []):
        relation_type = normalize_relation(item.get("relation_type", ""))
        if relation_type is None:
            warnings.append(
                f"非法关系类型: {item.get('relation_type')}(已跳过)"
            )
            continue
        source_key = f"{item.get('source')}_{item.get('source_id')}"
        target_key = f"{item.get('target')}_{item.get('target_id')}"
        if (
            str(item.get("source_id")) not in seen_ids.get(str(item.get("source")), set())
            or str(item.get("target_id"))
            not in seen_ids.get(str(item.get("target")), set())
        ):
            warnings.append(f"关系引用缺失: {source_key} -> {target_key}(已跳过)")
            continue
        relations.append(
            Relation(
                source=item.get("source", ""),
                source_id=item.get("source_id"),
                target=item.get("target", ""),
                target_id=item.get("target_id"),
                relation_type=RelationType(relation_type),
                provenance=provenance(item),
                confidence=item.get("confidence", 0.0),
            )
        )

    dataset = KnowledgeDataset(
        version=version,
        maps=maps,
        npcs=npcs,
        monsters=monsters,
        items=items,
        equipment=equipment,
        quests=quests,
        story_lore=story_lore,
        relations=relations,
    )
    result = ImportResult(
        source=source,
        version=version,
        imported_maps=len(maps),
        imported_npcs=len(npcs),
        imported_monsters=len(monsters),
        imported_items=len(items),
        imported_equipment=len(equipment),
        imported_quests=len(quests),
        imported_story_lore=len(story_lore),
        imported_relations=len(relations),
        warnings=warnings,
    )
    return dataset, result
