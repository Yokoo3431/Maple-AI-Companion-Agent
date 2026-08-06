"""知识库基础层单测:schema / loader / Provider 生命周期 / Mock / 版本检测。"""

import json

import pytest
from pydantic import ValidationError

from maple_agent.knowledge import detect_profile, load_profile
from maple_agent.knowledge.models import MapInfo
from maple_agent.logging_setup import setup_logging
from maple_agent.providers.base import ProviderError
from maple_agent.providers.knowledge import (
    JsonKnowledgeProvider,
    MockKnowledgeProvider,
)


def test_schema_validation():
    item = MapInfo(map_id=1, name="射手村", aliases=["Henesys"])
    assert item.aliases == ["Henesys"]
    with pytest.raises(ValidationError):
        MapInfo(map_id=1)  # 缺少 name


def _write_profile(tmp_path, version: str = "v113") -> None:
    profile_dir = tmp_path / "versions" / "maple-v113"
    profile_dir.mkdir(parents=True)
    (profile_dir / "profile.json").write_text(
        json.dumps({"game_profile": "maple-v113", "version": version}),
        encoding="utf-8",
    )
    (profile_dir / "maps.json").write_text(
        json.dumps(
            [
                {"map_id": 1, "name": "射手村", "aliases": ["Henesys"]},
                {"map_id": 2, "name": "勇士部落", "aliases": ["Perion"]},
            ]
        ),
        encoding="utf-8",
    )
    (profile_dir / "npc.json").write_text(
        json.dumps([{"npc_id": 101, "name": "赫丽娜", "map_id": 1}]),
        encoding="utf-8",
    )
    (profile_dir / "monster.json").write_text(
        json.dumps([{"monster_id": 100, "name": "绿水灵", "level": 1, "hp": 15}]),
        encoding="utf-8",
    )
    (profile_dir / "quests.json").write_text(
        json.dumps(
            [
                {
                    "quest_id": 1,
                    "name": "新手教学",
                    "npc_id": 101,
                    "map_id": 1,
                    "requirements": {"level": "1"},
                    "rewards": {"exp": "10"},
                }
            ]
        ),
        encoding="utf-8",
    )


def test_loader_json_and_version(tmp_path):
    _write_profile(tmp_path)
    data = load_profile(tmp_path / "versions" / "maple-v113", "maple-v113")
    assert data.version == "v113"
    assert data.counts == {"maps": 2, "npcs": 1, "monsters": 1, "quests": 1}
    assert data.to_dictionary().entries["射手村"] == ["Henesys"]


def test_loader_csv(tmp_path):
    profile_dir = tmp_path / "versions" / "maple-csv"
    profile_dir.mkdir(parents=True)
    (profile_dir / "maps.csv").write_text(
        "map_id,name,aliases,region\n1,射手村,\"Henesys,Hehe\",冒险岛世界\n",
        encoding="utf-8",
    )
    data = load_profile(profile_dir, "maple-csv")
    assert data.counts["maps"] == 1
    assert data.maps[0].aliases == ["Henesys", "Hehe"]


def test_detect_profile(tmp_path):
    _write_profile(tmp_path)
    assert detect_profile(tmp_path, "maple-v113") == (True, "v113")
    assert detect_profile(tmp_path, "missing-profile") == (False, "")
    assert detect_profile(tmp_path, "") == (False, "")


def test_json_provider_lifecycle_and_queries(tmp_path):
    _write_profile(tmp_path)
    provider = JsonKnowledgeProvider(
        knowledge_root=tmp_path,
        game_profile="maple-v113",
    )
    with pytest.raises(ProviderError):
        provider.get_map(1)  # 未初始化
    provider.initialize()
    assert provider.profile_status == "ok"
    assert provider.version == "v113"
    assert provider.get_map(1).name == "射手村"
    assert provider.get_map("勇士部落").map_id == 2
    assert provider.get_npc(101).name == "赫丽娜"
    assert provider.get_monster(100).name == "绿水灵"
    assert provider.get_quest_template(1).name == "新手教学"
    assert provider.resolve_alias("Henesys") == "射手村"
    assert provider.resolve_alias("不存在") is None
    assert provider.load_map_dictionary().entries["射手村"] == ["Henesys"]


def test_json_provider_missing_profile(tmp_path):
    provider = JsonKnowledgeProvider(
        knowledge_root=tmp_path,
        game_profile="missing-profile",
    )
    provider.initialize()
    assert provider.profile_status == "missing"
    assert provider.counts == {"maps": 0, "npcs": 0, "monsters": 0, "quests": 0}


def test_mock_knowledge_provider():
    provider = MockKnowledgeProvider()
    provider.initialize()
    assert provider.profile_status == "ok"
    assert provider.game_profile == "maple-v113"
    assert provider.resolve_alias("Perion") == "勇士部落"
    assert provider.counts["monsters"] == 1


def test_knowledge_lookup_trace(tmp_path):
    logs_dir = tmp_path / "logs"
    setup_logging(logs_dir, level="INFO", console=False)
    _write_profile(tmp_path)
    provider = JsonKnowledgeProvider(
        knowledge_root=tmp_path,
        game_profile="maple-v113",
    )
    provider.initialize()
    provider.get_map(1, trace_id="trace-knowledge-1")
    startup_log = (logs_dir / "startup.log").read_text(encoding="utf-8")
    assert "knowledge lookup: get_map" in startup_log
    assert "trace=trace-knowledge-1" in startup_log
