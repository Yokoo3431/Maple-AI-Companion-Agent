"""FailureAnalyzer:失败模式 -> 根因分析(只读)。"""

from __future__ import annotations

from maple_agent.failure_intelligence.models import (
    FailurePatternRecord,
    RootCauseAnalysis,
)


class FailureAnalyzer:
    """输出根因 / 风险等级 / 预防策略 / 建议调整。"""

    _PREVENTION = {
        "EXECUTION_FAILED": "执行前验证前置条件并启用重试",
        "WORLD_MISMATCH": "观察与计划交叉验证后再执行",
        "KNOWLEDGE_ERROR": "定期刷新知识库并校验实体",
        "LOW_CONFIDENCE": "低置信动作必须人工确认",
        "OBSERVATION_FAILED": "截图前检查窗口与 OCR 状态",
    }

    def analyze(
        self,
        *,
        pattern: FailurePatternRecord,
        match_score: float = 0.0,
    ) -> RootCauseAnalysis:
        risk_level = self._risk(pattern, match_score)
        prevention = self._PREVENTION.get(
            pattern.failure_type,
            "增加人工检查点",
        )
        adjustment = (
            f"在任务 {', '.join(pattern.affected_tasks) or '未知'} "
            "前增加恢复点"
        )
        return RootCauseAnalysis(
            pattern_id=pattern.pattern_id,
            root_cause=pattern.root_cause,
            risk_level=risk_level,
            prevention_strategy=prevention,
            recommended_adjustment=adjustment,
        )

    @staticmethod
    def _risk(
        pattern: FailurePatternRecord,
        match_score: float,
    ) -> str:
        combined = match_score * 0.6 + (1 - pattern.success_rate) * 0.4
        if combined >= 0.6:
            return "HIGH"
        if combined >= 0.3:
            return "MEDIUM"
        return "LOW"
