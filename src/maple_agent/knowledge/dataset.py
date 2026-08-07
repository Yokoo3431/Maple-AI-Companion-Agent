"""Knowledge Dataset:外部 JSON 知识数据加载(Phase 4-B,失败安全降级)。"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import BaseModel, Field

from maple_agent.knowledge_graph.models import (
    ItemNode,
    MapNode,
    MonsterNode,
    NPCNode,
    Relation,
)

logger = logging.getLogger("maple_agent.knowledge")


class KnowledgeDataset(BaseModel):
    """外部知识数据集。"""

    version: str = "v1"
    maps: list[MapNode] = Field(default_factory=list)
    npcs: list[NPCNode] = Field(default_factory=list)
    monsters: list[MonsterNode] = Field(default_factory=list)
    items: list[ItemNode] = Field(default_factory=list)
    relations: list[Relation] = Field(default_factory=list)


def _load_list(path: Path, model) -> list:
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, list):
            logger.warning("dataset 非法结构(非列表): %s", path)
            return []
        return [model.model_validate(item) for item in raw]
    except Exception as exc:
        logger.warning("dataset 加载失败,安全降级: %s (%s)", path, exc)
        return []


def load_dataset(directory: str | Path | None = None) -> KnowledgeDataset:
    """加载 src/maple_agent/knowledge/data/ 下的 JSON 数据集。"""
    data_dir = (
        Path(directory)
        if directory is not None
        else Path(__file__).resolve().parent / "data"
    )
    dataset = KnowledgeDataset()
    meta = data_dir / "dataset.json"
    if meta.exists():
        try:
            dataset.version = str(
                json.loads(meta.read_text(encoding="utf-8")).get("version", "v1")
            )
        except Exception as exc:
            logger.warning("dataset 版本读取失败: %s", exc)
    dataset.maps = _load_list(data_dir / "maps.json", MapNode)
    dataset.npcs = _load_list(data_dir / "npcs.json", NPCNode)
    dataset.monsters = _load_list(data_dir / "monsters.json", MonsterNode)
    dataset.items = _load_list(data_dir / "items.json", ItemNode)
    dataset.relations = _load_list(data_dir / "relations.json", Relation)
    logger.info(
        "knowledge dataset loaded: version=%s maps=%d npcs=%d monsters=%d items=%d relations=%d",
        dataset.version,
        len(dataset.maps),
        len(dataset.npcs),
        len(dataset.monsters),
        len(dataset.items),
        len(dataset.relations),
    )
    return dataset
