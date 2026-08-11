"""MemoryGraphValidator:记忆节点校验(只读)。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field

from maple_agent.memory_graph.models import (
    MemoryNode,
    MemoryRelationType,
    MemoryType,
)


class MemoryGraphVerdict(StrEnum):
    """记忆校验结论。"""

    VALID = "VALID"
    WARNING = "WARNING"
    BLOCKED = "BLOCKED"


class MemoryNodeValidationResult(BaseModel):
    """单节点校验结果。"""

    memory_id: str
    verdict: MemoryGraphVerdict
    issues: list[str] = Field(default_factory=list)


class MemoryGraphValidator:
    """检查 id / 类型 / 置信度 / 上下文 / 关系。"""

    def validate_node(
        self,
        node: MemoryNode,
    ) -> MemoryNodeValidationResult:
        issues: list[str] = []
        if not node.memory_id:
            issues.append("缺少 memory_id")
        if node.memory_type not in set(MemoryType):
            issues.append("未知 memory type")
        if not (0 <= node.confidence <= 1):
            issues.append("confidence 越界")
        blocked = bool(issues)
        for relation in node.relations:
            if relation.relation_type not in set(MemoryRelationType):
                issues.append("损坏 relation")
                blocked = True
                break
        if blocked:
            return MemoryNodeValidationResult(
                memory_id=node.memory_id,
                verdict=MemoryGraphVerdict.BLOCKED,
                issues=issues,
            )
        if not node.context:
            issues.append("缺少 context")
        if not node.relations:
            issues.append("缺少 relation")
        verdict = (
            MemoryGraphVerdict.VALID
            if not issues
            else MemoryGraphVerdict.WARNING
        )
        return MemoryNodeValidationResult(
            memory_id=node.memory_id,
            verdict=verdict,
            issues=issues,
        )

    def validate_graph(
        self,
        nodes: list[MemoryNode],
    ) -> list[MemoryNodeValidationResult]:
        return [self.validate_node(node) for node in nodes]
