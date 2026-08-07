"""DecisionEvaluator:选项校验 / 比较 / 解释(只读决策建模)。"""

from __future__ import annotations

from pydantic import BaseModel

from maple_agent.decision.models import DecisionOption, DecisionResult
from maple_agent.goal.models import Goal


class OptionVerdict(BaseModel):
    """单个选项的校验结论。"""

    option_id: str
    valid: bool
    reason: str


class ComparisonResult(BaseModel):
    """两两比较结论。"""

    better_option_id: str
    reason: str


ALLOWED_ACTIONS = frozenset(
    {
        "OBSERVE",
        "ANALYZE",
        "QUERY_KNOWLEDGE",
        "WAIT",
        "PAUSE",
        "TALK",
        "COLLECT",
        "DEFEAT",
        "DELIVER",
        "COMPLETE",
        "MOVE_HINT",
    }
)


class DecisionEvaluator:
    """校验候选决策并生成解释;禁止任何物理动作语义。"""

    def __init__(
        self,
        *,
        min_confidence: float = 0.4,
        max_risk: float = 0.8,
    ) -> None:
        self.min_confidence = min_confidence
        self.max_risk = max_risk

    def evaluate(self, option: DecisionOption) -> OptionVerdict:
        """检查 action 合法性 / 置信度下限 / 风险上限。"""
        if not option.decision_id:
            return OptionVerdict(
                option_id=option.decision_id,
                valid=False,
                reason="decision_id 为空",
            )
        if not option.action:
            return OptionVerdict(
                option_id=option.decision_id,
                valid=False,
                reason="action 为空",
            )
        if option.action not in ALLOWED_ACTIONS:
            return OptionVerdict(
                option_id=option.decision_id,
                valid=False,
                reason=f"非法 action: {option.action}",
            )
        if option.confidence < self.min_confidence:
            return OptionVerdict(
                option_id=option.decision_id,
                valid=False,
                reason=(
                    f"置信度过低: {option.confidence:.2f} < "
                    f"{self.min_confidence:.2f}"
                ),
            )
        if option.risk > self.max_risk:
            return OptionVerdict(
                option_id=option.decision_id,
                valid=False,
                reason=f"风险过高: {option.risk:.2f} > {self.max_risk:.2f}",
            )
        return OptionVerdict(
            option_id=option.decision_id,
            valid=True,
            reason="有效",
        )

    def compare(
        self,
        left: DecisionOption,
        right: DecisionOption,
        *,
        scores: dict[str, float] | None = None,
    ) -> ComparisonResult:
        """优先按得分比较;无得分时按置信度/风险启发式。"""
        left_score = scores.get(left.decision_id) if scores else None
        right_score = scores.get(right.decision_id) if scores else None
        if left_score is not None and right_score is not None:
            if left_score != right_score:
                better = left if left_score > right_score else right
                return ComparisonResult(
                    better_option_id=better.decision_id,
                    reason=(
                        f"得分更高({max(left_score, right_score):.4f} > "
                        f"{min(left_score, right_score):.4f})"
                    ),
                )
            return ComparisonResult(
                better_option_id=left.decision_id,
                reason="得分相同",
            )
        if left.confidence != right.confidence:
            better = left if left.confidence > right.confidence else right
            return ComparisonResult(
                better_option_id=better.decision_id,
                reason="置信度更高",
            )
        if left.risk != right.risk:
            better = left if left.risk < right.risk else right
            return ComparisonResult(
                better_option_id=better.decision_id,
                reason="风险更低",
            )
        return ComparisonResult(
            better_option_id=left.decision_id,
            reason="两者等价",
        )

    def explain(
        self,
        result: DecisionResult,
        *,
        goal: Goal | None = None,
    ) -> str:
        """生成人类可读的决策解释。"""
        if result.selected_option is None:
            reasons = "；".join(
                self.evaluate(option).reason for option in result.rejected
            )
            return f"无有效决策: {reasons or '无候选决策'}"
        goal_title = goal.title if goal is not None else "-"
        selected = result.selected_option
        return (
            f"目标「{goal_title}」下选择 {selected.decision_id} "
            f"({selected.action} → {selected.target or '-'}),"
            f" 得分 {result.score:.2f}, 备选 {len(result.alternatives) - 1} 个"
        )
