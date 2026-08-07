"""Normalization:名称/别名/关系归一化。"""

from __future__ import annotations

import re

from maple_agent.knowledge_graph.models import RelationType

_INVALID_CHARS = re.compile(r"[^\w\u4e00-\u9fff\s\-]")
_RELATION_TYPES = {item.value for item in RelationType}


def normalize_name(name: str) -> str:
    """去空白、非法字符。"""
    if not isinstance(name, str):
        return ""
    collapsed = " ".join(name.split()).strip()
    return _INVALID_CHARS.sub("", collapsed)


def normalize_alias(aliases: list[str]) -> list[str]:
    """去空白、去重、过滤空值。"""
    seen: list[str] = []
    for alias in aliases:
        normalized = normalize_name(alias)
        if normalized and normalized not in seen:
            seen.append(normalized)
    return seen


def normalize_relation(relation_type: str) -> str | None:
    """关系类型归一化;非法返回 None。"""
    if not isinstance(relation_type, str):
        return None
    normalized = relation_type.strip().upper().replace("-", "_").replace(" ", "_")
    return normalized if normalized in _RELATION_TYPES else None
