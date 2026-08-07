"""Knowledge Retrieval 单测:exact / alias / fuzzy / ranking / context / fusion。"""

import json

from maple_agent.fusion import FusionService
from maple_agent.knowledge.retrieval import AliasIndex, EntityRanker
from maple_agent.knowledge.retrieval.models import CandidateEntity
from maple_agent.knowledge_graph import build_graph
from maple_agent.providers.knowledge import JsonKnowledgeProvider
from maple_agent.vision import Observation


def _index():
    provider = JsonKnowledgeProvider()
    provider.initialize()
    return AliasIndex.from_graph(build_graph(provider))


def test_exact_match():
    index = _index()
    best = index.search("射手村", entity_type="map")[0]
    assert best.source == "exact"
    assert best.score == 1.0


def test_alias_match():
    index = _index()
    best = index.search("Henesys", entity_type="map")[0]
    assert best.source == "alias"
    assert best.score == 0.95
    assert best.text == "射手村"


def test_prefix_match():
    index = _index()
    best = index.search("废弃都", entity_type="map")[0]
    assert best.source == "prefix"
    assert best.text == "废弃都市"


def test_fuzzy_match():
    index = _index()
    best = index.search("射手付", entity_type="map")[0]
    assert best.source == "fuzzy"
    assert best.text == "射手村"
    assert 0.0 < best.score < 0.7


def test_priority_exact_over_fuzzy():
    index = _index()
    exact = index.search("射手村", entity_type="map")
    fuzzy = index.search("射手付", entity_type="map")
    assert exact[0].source == "exact"
    assert fuzzy[0].source == "fuzzy"
    assert exact[0].score > fuzzy[0].score


def test_ranker_context_score():
    ranker = EntityRanker()
    candidates = [
        CandidateEntity(entity_id=1, entity_type="map", text="射手村", score=0.95),
        CandidateEntity(entity_id=101, entity_type="npc", text="赫丽娜", score=0.8),
    ]
    result = ranker.rank("x", candidates, ocr_confidence=0.9, context_hits={"npc"})
    assert result.best.entity_type == "npc"
    assert "context=npc" in result.best.reason


def test_fusion_uses_retrieval_ranking(tmp_path):
    provider = JsonKnowledgeProvider()
    provider.initialize()
    fusion = FusionService(
        provider,
        graph=build_graph(provider),
        sessions_dir=tmp_path / "sessions",
    )
    world = fusion.fuse(
        [
            Observation(
                element="ocr_text",
                type="text",
                raw_value="射手付",
                normalized_value="射手付",
                confidence=0.9,
                source="mock",
            )
        ],
        trace_id="trace-retrieval-fuzzy",
    )
    assert world.current_map is not None
    assert world.current_map.name == "射手村"
    replay = json.loads(
        (
            tmp_path
            / "sessions"
            / "trace-retrieval-fuzzy"
            / "knowledge_match.json"
        ).read_text(encoding="utf-8")
    )
    assert replay["candidate_scores"]
    assert "top=" in replay["ranking_reason"]
