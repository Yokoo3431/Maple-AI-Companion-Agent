"""KnowledgeSourceAdapter:外部静态来源 -> import packet(不直接写 Graph)。"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Protocol

import yaml

from maple_agent.knowledge_quality.models import KnowledgeSourceReference


class KnowledgeSourceAdapter(Protocol):
    """来源适配器契约:source -> structured import packet。"""

    adapter_name: str
    adapter_version: str

    def load(
        self,
        source: KnowledgeSourceReference,
    ) -> dict: ...


class LocalStaticKnowledgeAdapter:
    """真实可运行:读取本地 JSON/YAML 静态文件(或直接 dict)。"""

    adapter_name = "LocalStaticKnowledgeAdapter"
    adapter_version = "1.0"

    def __init__(self, base_dir: str | Path | None = None) -> None:
        self.base_dir = Path(base_dir) if base_dir else None
        self.last_packet: dict = {}

    def load(
        self,
        source: KnowledgeSourceReference,
    ) -> dict:
        reference = source.source_reference
        if isinstance(reference, str) and reference:
            path = (
                Path(reference)
                if Path(reference).is_absolute()
                else (self.base_dir / reference if self.base_dir else Path(reference))
            )
            content = path.read_text(encoding="utf-8")
            suffix = path.suffix.lower()
            packet = (
                yaml.safe_load(content)
                if suffix in (".yaml", ".yml")
                else json.loads(content)
            )
        else:
            packet = json.loads(reference) if reference else {}
        self.last_packet = packet if isinstance(packet, dict) else {}
        return self.last_packet


class ManualCuratedAdapter:
    """把内置 demo 数据包装为 MANUAL_CURATED import packet(完整 provenance)。"""

    adapter_name = "ManualCuratedAdapter"
    adapter_version = "1.0"

    def __init__(self) -> None:
        self.last_packet: dict = {}

    def load(
        self,
        source: KnowledgeSourceReference,
    ) -> dict:
        from maple_agent.maple_knowledge import load_demo_knowledge
        from maple_agent.spatial_world import load_demo_spatial_map
        from maple_agent.world_knowledge import load_demo_world_map

        entities, relations = load_demo_knowledge()
        world = load_demo_world_map()
        spatial = load_demo_spatial_map()
        packet = {
            "maps": world.get("maps", []),
            "connections": world.get("connections", []),
            "entities": [
                entity.model_dump(mode="json") for entity in entities
            ],
            "relations": [
                relation.model_dump(mode="json") for relation in relations
            ],
            "spatial_maps": spatial.get("maps", []),
        }
        self.last_packet = packet
        return packet


class WikiCommunityAdapter:
    """离线 snapshot 导入(预留;不访问互联网;无 snapshot 时返回空)。"""

    adapter_name = "WikiCommunityAdapter"
    adapter_version = "1.0"

    def __init__(self) -> None:
        self.last_packet: dict = {}

    def load(
        self,
        source: KnowledgeSourceReference,
    ) -> dict:
        reference = source.source_reference
        if reference and Path(reference).exists():
            packet = json.loads(
                Path(reference).read_text(encoding="utf-8")
            )
            self.last_packet = packet if isinstance(packet, dict) else {}
            return self.last_packet
        self.last_packet = {}
        return {}


class StaticGameResourceAdapter:
    """离线静态游戏资源(协议 stub;未实现 WZ parser,不编造万能解析)。"""

    adapter_name = "StaticGameResourceAdapter"
    adapter_version = "1.0"

    def __init__(self) -> None:
        self.last_packet: dict = {}

    def load(
        self,
        source: KnowledgeSourceReference,
    ) -> dict:
        # 预留:未来允许用户选择 Maple 客户端静态资源目录做离线导入。
        # 本阶段仅提供 manifest/validation contract,不解析资源格式。
        self.last_packet = {}
        return {}


def content_hash(packet: dict) -> str:
    """确定性内容哈希(用于 provenance / manifest)。"""
    payload = json.dumps(packet, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def sanitize_source_metadata(source: KnowledgeSourceReference | dict) -> dict:
    """Serialize source metadata without leaking source paths or raw packets."""
    data = (
        source.model_dump(mode="json")
        if isinstance(source, KnowledgeSourceReference)
        else dict(source)
    )
    for key in ("source_reference", "path", "private_path", "session_path"):
        if data.get(key):
            data[key] = "<REDACTED_PATH>"
    for key, value in list(data.items()):
        if isinstance(value, str) and ("\\" in value or ":/" in value):
            data[key] = "<REDACTED_PATH>"
    return data
