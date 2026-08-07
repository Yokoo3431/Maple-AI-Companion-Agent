"""知识库加载:JSON/CSV 人工导入 + Pydantic 校验 + 版本检测。"""

from __future__ import annotations

import csv
import json
from dataclasses import dataclass, field
from pathlib import Path

from maple_agent.knowledge.models import (
    MapDictionary,
    MapInfo,
    MonsterInfo,
    NpcInfo,
    QuestTemplate,
)
from maple_agent.quest.models import Quest


@dataclass
class KnowledgeData:
    """一个 game_profile 的加载结果。"""

    game_profile: str = ""
    version: str = ""
    maps: list[MapInfo] = field(default_factory=list)
    npcs: list[NpcInfo] = field(default_factory=list)
    monsters: list[MonsterInfo] = field(default_factory=list)
    quests: list[QuestTemplate] = field(default_factory=list)
    quests_domain: list[Quest] = field(default_factory=list)

    @property
    def counts(self) -> dict[str, int]:
        return {
            "maps": len(self.maps),
            "npcs": len(self.npcs),
            "monsters": len(self.monsters),
            "quests": len(self.quests),
        }

    def to_dictionary(self) -> MapDictionary:
        entries: dict[str, list[str]] = {}
        for item in self.maps:
            entries[item.name] = item.aliases
        return MapDictionary(entries=entries)


def _read_json_or_csv(path_stem: Path) -> list[dict]:
    json_path = Path(f"{path_stem}.json")
    csv_path = Path(f"{path_stem}.csv")
    if json_path.exists():
        raw = json.loads(json_path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, list) else []
    if csv_path.exists():
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            return [_normalize_row(row) for row in csv.DictReader(handle)]
    return []


def _normalize_row(row: dict) -> dict:
    """CSV 的列表字段(aliases 等)按逗号拆分。"""
    out: dict = {}
    for key, value in row.items():
        if key in {"aliases"} and isinstance(value, str):
            out[key] = [part.strip() for part in value.split(",") if part.strip()]
        else:
            out[key] = value
    return out


def load_profile(profile_dir: Path, game_profile: str) -> KnowledgeData:
    """加载并 Pydantic 校验一个 game_profile 目录(JSON 或 CSV)。"""
    data = KnowledgeData(game_profile=game_profile, version=game_profile)
    profile_json = profile_dir / "profile.json"
    if profile_json.exists():
        try:
            meta = json.loads(profile_json.read_text(encoding="utf-8"))
            data.version = str(meta.get("version", game_profile))
        except (json.JSONDecodeError, OSError):
            pass
    data.maps = [MapInfo.model_validate(item) for item in _read_json_or_csv(profile_dir / "maps")]
    data.npcs = [NpcInfo.model_validate(item) for item in _read_json_or_csv(profile_dir / "npc")]
    data.monsters = [
        MonsterInfo.model_validate(item) for item in _read_json_or_csv(profile_dir / "monster")
    ]
    data.quests = [
        QuestTemplate.model_validate(item) for item in _read_json_or_csv(profile_dir / "quests")
    ]
    data.quests_domain = [
        Quest.model_validate(item)
        for item in _read_json_or_csv(profile_dir / "quests_domain")
    ]
    return data


def detect_profile(knowledge_root: Path, game_profile: str) -> tuple[bool, str]:
    """检测 profile 是否存在;返回 (存在?, 版本)。"""
    if not game_profile:
        return False, ""
    profile_dir = knowledge_root / "versions" / game_profile
    if not profile_dir.exists():
        return False, ""
    version = game_profile
    profile_json = profile_dir / "profile.json"
    if profile_json.exists():
        try:
            meta = json.loads(profile_json.read_text(encoding="utf-8"))
            version = str(meta.get("version", game_profile))
        except (json.JSONDecodeError, OSError):
            pass
    return True, version
