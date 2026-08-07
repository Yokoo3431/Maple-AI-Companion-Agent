"""DecisionEngine:目标对齐 + 知识置信 + 风险惩罚 + 排序选择(只读)。"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from maple_agent.decision.evaluator import DecisionEvaluator
from maple_agent.decision.models import DecisionContext, DecisionOption, DecisionResult
from maple_agent.goal.models import Goal, GoalType
from maple_agent.logging_setup import TraceContext

logger = logging.getLogger("maple_agent.decision")

_DEFAULT_ALIGNMENT = 0.4

GOAL_ALIGNMENT: dict[GoalType, dict[str, float]] = {
    GoalType.QUEST: {
        "TALK": 1.0,
        "DELIVER": 1.0,
        "COMPLETE": 1.0,
        "COLLECT": 0.9,
        "DEFEAT": 0.8,
        "MOVE_HINT": 0.6,
        "ANALYZE": 0.5,
        "OBSERVE": 0.4,
        "QUERY_KNOWLEDGE": 0.4,
        "WAIT": 0.2,
        "PAUSE": 0.0,
    },
    GoalType.LEVELING: {
        "DEFEAT": 1.0,
        "MOVE_HINT": 0.8,
        "COLLECT": 0.6,
        "ANALYZE": 0.5,
        "OBSERVE": 0.4,
        "QUERY_KNOWLEDGE": 0.4,
        "TALK": 0.3,
        "DELIVER": 0.3,
        "COMPLETE": 0.3,
        "WAIT": 0.1,
        "PAUSE": 0.0,
    },
    GoalType.EXPLORATION: {
        "MOVE_HINT": 1.0,
        "OBSERVE": 0.9,
        "ANALYZE": 0.8,
        "QUERY_KNOWLEDGE": 0.7,
        "WAIT": 0.3,
        "PAUSE": 0.1,
        "TALK": 0.3,
        "COLLECT": 0.4,
        "DEFEAT": 0.2,
        "DELIVER": 0.2,
        "COMPLETE": 0.2,
    },
    GoalType.COLLECTION: {
        "COLLECT": 1.0,
        "DEFEAT": 0.7,
        "MOVE_HINT": 0.7,
        "ANALYZE": 0.4,
        "OBSERVE": 0.4,
        "QUERY_KNOWLEDGE": 0.4,
        "TALK": 0.3,
        "DELIVER": 0.3,
        "COMPLETE": 0.3,
        "WAIT": 0.1,
        "PAUSE": 0.0,
    },
    GoalType.MAINTENANCE: {
        "OBSERVE": 0.8,
        "WAIT": 0.7,
        "ANALYZE": 0.6,
        "QUERY_KNOWLEDGE": 0.6,
        "PAUSE": 0.4,
        "TALK": 0.3,
        "COLLECT": 0.2,
        "DEFEAT": 0.1,
        "DELIVER": 0.2,
        "COMPLETE": 0.2,
        "MOVE_HINT": 0.3,
    },
    GoalType.CUSTOM: {
        "ANALYZE": 0.8,
        "OBSERVE": 0.7,
        "QUERY_KNOWLEDGE": 0.7,
        "TALK": 0.6,
        "COLLECT": 0.6,
        "DEFEAT": 0.5,
        "DELIVER": 0.5,
        "COMPLETE": 0.5,
        "MOVE_HINT": 0.5,
        "WAIT": 0.3,
        "PAUSE": 0.1,
    },
}


class DecisionEngine:
    """把候选选项按目标/知识/风险评分并选择最优(仅推荐)。"""

    def __init__(
        self,
        *,
        evaluator: DecisionEvaluator | None = None,
        sessions_dir: str | Path = "sessions",
        goal_weight: float = 0.5,
        knowledge_weight: float = 0.3,
        risk_weight: float = 0.2,
    ) -> None:
        self.evaluator = evaluator or DecisionEvaluator()
        self.sessions_dir = Path(sessions_dir)
        self.goal_weight = goal_weight
        self.knowledge_weight = knowledge_weight
        self.risk_weight = risk_weight
        self.last_result: DecisionResult | None = None

    def decide(
        self,
        context: DecisionContext,
        *,
        trace_id: str | None = None,
    ) -> DecisionResult:
        """输入 DecisionContext,输出 DecisionResult(只读,不执行)。"""
        with TraceContext(trace_id=trace_id) as trace:
            scored: list[tuple[float, DecisionOption]] = []
            rejected: list[DecisionOption] = []
            for option in context.options:
                verdict = self.evaluator.evaluate(option)
                if not verdict.valid:
                    rejected.append(option)
                    logger.info(
                        "decision rejected: %s (%s)",
                        option.decision_id,
                        verdict.reason,
                    )
                    continue
                score = self._score(option, context)
                scored.append((score, option))
                logger.info(
                    "decision scored: %s score=%.4f",
                    option.decision_id,
                    score,
                )
            scored.sort(key=lambda item: item[0], reverse=True)
            alternatives = [option for _, option in scored]
            selected = alternatives[0] if alternatives else None
            selected_score = scored[0][0] if scored else 0.0
            result = DecisionResult(
                selected_option=selected,
                alternatives=alternatives,
                rejected=rejected,
                score=selected_score,
                trace_id=trace.trace_id,
            )
            result = result.model_copy(
                update={
                    "explanation": self.evaluator.explain(
                        result,
                        goal=context.goal,
                    )
                }
            )
            self.last_result = result
            self._write_replay(context, result, scored, trace.trace_id)
            return result

    def _score(
        self,
        option: DecisionOption,
        context: DecisionContext,
    ) -> float:
        goal_score = self._goal_alignment(option.action, context.goal)
        knowledge_score = option.confidence * self._context_confidence(context)
        raw = (
            self.goal_weight * goal_score
            + self.knowledge_weight * knowledge_score
            - self.risk_weight * option.risk
        )
        return round(max(0.0, min(1.0, raw)), 4)

    @staticmethod
    def _context_confidence(context: DecisionContext) -> float:
        if context.knowledge_state is not None:
            return context.knowledge_state.confidence
        if context.world_state is not None:
            return context.world_state.confidence
        return 0.0

    @staticmethod
    def _goal_alignment(action: str, goal: Goal | None) -> float:
        if goal is None:
            return _DEFAULT_ALIGNMENT
        table = GOAL_ALIGNMENT.get(
            goal.goal_type,
            GOAL_ALIGNMENT[GoalType.CUSTOM],
        )
        return table.get(action, _DEFAULT_ALIGNMENT)

    def _write_replay(
        self,
        context: DecisionContext,
        result: DecisionResult,
        scored: list[tuple[float, DecisionOption]],
        trace_id: str,
    ) -> None:
        directory = self.sessions_dir / trace_id
        directory.mkdir(parents=True, exist_ok=True)
        payload = {
            "trace_id": trace_id,
            "goal": (
                context.goal.model_dump(mode="json")
                if context.goal is not None
                else None
            ),
            "candidate_decisions": [
                {
                    "option": option.model_dump(mode="json"),
                    "score": score,
                }
                for score, option in scored
            ],
            "rejected": [
                option.model_dump(mode="json") for option in result.rejected
            ],
            "selected": (
                result.selected_option.model_dump(mode="json")
                if result.selected_option is not None
                else None
            ),
            "selected_score": result.score,
            "selected_reason": result.explanation,
        }
        (directory / "decision_trace.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
