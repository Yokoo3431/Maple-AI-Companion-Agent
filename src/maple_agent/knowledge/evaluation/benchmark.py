"""RetrievalBenchmark:检索性能基准(毫秒级查询,面向 5000+ 实体规模)。"""

from __future__ import annotations

import json
import time
from pathlib import Path

from maple_agent.knowledge.retrieval import AliasIndex
from maple_agent.knowledge_graph.models import MapNode


def build_scaled_index(entity_count: int) -> AliasIndex:
    """构造指定规模的合成索引(评估扩展性)。"""

    class _GraphView:
        def __init__(self) -> None:
            self.maps = [
                MapNode(
                    map_id=index,
                    name=f"地图{index:06d}",
                    aliases=[f"d{index}", f"map{index}"],
                )
                for index in range(1, entity_count + 1)
            ]
            self.npcs: list = []
            self.monsters: list = []
            self.items: list = []

    return AliasIndex.from_graph(_GraphView())


class RetrievalBenchmark:
    def __init__(self, index: AliasIndex) -> None:
        self.index = index

    def run(
        self,
        queries: list[str],
        *,
        repeat: int = 5,
        entity_count: int | None = None,
    ) -> dict:
        if not queries:
            return {"entities": 0, "queries": 0, "avg_ms": 0.0, "max_ms": 0.0}
        samples: list[float] = []
        for _ in range(repeat):
            for query in queries:
                start = time.perf_counter()
                self.index.search(query)
                samples.append((time.perf_counter() - start) * 1000)
        return {
            "entities": entity_count or len(self.index.all()),
            "queries": len(queries),
            "avg_ms": round(sum(samples) / len(samples), 4),
            "max_ms": round(max(samples), 4),
        }

    def save(self, data: dict, path: str | Path) -> None:
        Path(path).write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
