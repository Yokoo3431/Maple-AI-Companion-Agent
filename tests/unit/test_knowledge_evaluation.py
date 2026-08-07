"""Knowledge Evaluation 单测:benchmark 加载 / Top1 / TopK / fuzzy / alias / 降级 / Replay。"""

import json

from maple_agent.context import ContextBuilder
from maple_agent.fusion import FusionService
from maple_agent.knowledge.evaluation import (
    EvaluationRunner,
    RetrievalBenchmark,
    load_retrieval_cases,
)
from maple_agent.knowledge.evaluation.benchmark import build_scaled_index
from maple_agent.knowledge_graph import build_graph
from maple_agent.providers.knowledge import JsonKnowledgeProvider
from maple_agent.vision import Observation


def _setup():
    provider = JsonKnowledgeProvider()
    provider.initialize()
    return provider, build_graph(provider)


def test_benchmark_cases_loaded():
    cases = load_retrieval_cases()
    assert len(cases) >= 50
    assert cases[0].case_id == "case001"
    assert cases[0].expected_entity_id == "map_1"
    assert cases[0].expected_entity_type == "map"


def test_top1_correct():
    _, graph = _setup()
    runner = EvaluationRunner.from_graph(graph)
    exact = [case for case in load_retrieval_cases() if case.difficulty == "exact"]
    result = runner.run(exact)
    assert result.top1_accuracy == 1.0
    assert result.correct_top1 == len(exact)


def test_topk_recall():
    _, graph = _setup()
    runner = EvaluationRunner.from_graph(graph)
    result = runner.run(load_retrieval_cases())
    assert result.top3_recall >= result.top1_accuracy
    assert result.top3_recall > 0.8


def test_fuzzy_cases_partial_hit():
    _, graph = _setup()
    runner = EvaluationRunner.from_graph(graph)
    fuzzy = [
        case
        for case in load_retrieval_cases()
        if case.difficulty in ("fuzzy", "homophone", "ocr_garbled", "similar", "short")
    ]
    result = runner.run(fuzzy)
    assert result.top3_recall > 0


def test_alias_cases_high_accuracy():
    _, graph = _setup()
    runner = EvaluationRunner.from_graph(graph)
    alias = [case for case in load_retrieval_cases() if case.difficulty == "alias"]
    result = runner.run(alias)
    assert result.top1_accuracy >= 0.9


def test_empty_data_degrades():
    _, graph = _setup()
    runner = EvaluationRunner.from_graph(graph)
    result = runner.run([])
    assert result.total_cases == 0
    assert result.top1_accuracy == 0.0
    assert result.top3_recall == 0.0


def test_replay_evaluation_context(tmp_path):
    provider, graph = _setup()
    fusion = FusionService(
        provider,
        graph=graph,
        sessions_dir=tmp_path / "sessions",
    )
    fusion.fuse(
        [
            Observation(
                element="ocr_text",
                type="text",
                raw_value="射手村1",
                normalized_value="射手村1",
                confidence=0.9,
                source="mock",
            )
        ],
        trace_id="trace-eval-ctx",
    )
    replay = json.loads(
        (
            tmp_path
            / "sessions"
            / "trace-eval-ctx"
            / "knowledge_match.json"
        ).read_text(encoding="utf-8")
    )
    ctx = replay["evaluation_context"]
    assert ctx["index_version"] == "v1"
    assert ctx["dataset_version"] == "v1"
    assert ctx["retrieval_strategy"] == "exact_alias_prefix_fuzzy"
    assert ctx["candidate_count"] >= 1


def test_scaled_benchmark_millisecond():
    index = build_scaled_index(2000)
    bench = RetrievalBenchmark(index).run(
        ["地图000001", "地图000999", "d42", "地图000021", "map3"]
    )
    assert bench["entities"] == 2000
    assert bench["queries"] == 5
    assert bench["avg_ms"] < 50


def test_context_retrieval_metrics():
    provider, graph = _setup()
    fusion = FusionService(provider, graph=graph)
    world = fusion.fuse(
        [
            Observation(
                element="ocr_text",
                type="text",
                raw_value="射手村",
                normalized_value="射手村",
                confidence=0.95,
                source="mock",
            )
        ],
        trace_id="trace-metrics",
    )
    context = ContextBuilder(provider).build(
        vision_state=None,
        world_state=world,
        runtime_state="READY",
        trace_id="trace-metrics",
    )
    assert context.knowledge_state.retrieval_metrics is not None
    assert context.knowledge_state.retrieval_metrics.candidate_count >= 3
    assert context.knowledge_state.retrieval_metrics.confidence_level == "HIGH"
