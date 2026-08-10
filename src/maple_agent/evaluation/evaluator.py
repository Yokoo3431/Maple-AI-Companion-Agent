"""五个组件评估器:Decision / Plan / Execution / Reflection / Memory(只读)。"""

from __future__ import annotations

from pydantic import BaseModel, Field

from maple_agent.experience.store import ExperienceStore


class EvaluationComponent(BaseModel):
    """单个组件的评分结果。"""

    score: float = Field(default=0.0, ge=0, le=1)
    issues: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)


def _clamp(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 4)


class DecisionEvaluator:
    """分析 decision_trace.json:候选选择 / 知识置信 / 经验利用 / 风险。"""

    def evaluate(self, trace: dict) -> EvaluationComponent:
        score = 0.5
        issues: list[str] = []
        recommendations: list[str] = []
        candidates = trace.get("candidate_decisions") or []
        selected = trace.get("selected")
        if candidates and selected:
            top_id = candidates[0]["option"]["decision_id"]
            if selected["decision_id"] == top_id:
                score += 0.25
            else:
                issues.append("未选择最高评分候选")
                recommendations.append("应选择评分最高的候选")
        selected_score = trace.get("selected_score", 0)
        if selected_score >= 0.5:
            score += 0.1
        else:
            issues.append("决策得分偏低")
        experience = trace.get("experience")
        if experience is not None and experience.get("retrieved"):
            score += 0.1
        else:
            recommendations.append("可接入经验库提升决策质量")
        if selected is not None:
            risk = selected.get("risk", 0)
            if risk > 0.8:
                score -= 0.25
                issues.append("存在高风险选择")
                recommendations.append("应避免高风险动作")
        return EvaluationComponent(
            score=_clamp(score),
            issues=issues,
            recommendations=recommendations,
        )


class PlanEvaluator:
    """分析 action_plan_trace.json:校验 / 前置 / 步骤完整度。"""

    def evaluate(self, trace: dict) -> EvaluationComponent:
        score = 0.5
        issues: list[str] = []
        recommendations: list[str] = []
        validation = trace.get("validation_result") or {}
        if validation.get("valid"):
            score += 0.2
        else:
            errors = validation.get("errors") or []
            issues.append("计划校验未通过: " + "; ".join(errors))
            recommendations.append("修复计划校验问题后重试")
        steps = trace.get("generated_steps") or []
        if len(steps) >= 2:
            score += 0.15
        elif steps:
            score += 0.05
        else:
            issues.append("计划缺少步骤")
        prerequisites = trace.get("prerequisites") or []
        missing = [
            item for item in prerequisites if str(item).startswith("缺失:")
        ]
        if not missing and prerequisites:
            score += 0.15
        elif missing:
            issues.append("存在不可满足前置: " + "; ".join(missing))
        if len(steps) > 8:
            issues.append("步骤冗余")
            recommendations.append("精简执行步骤")
            score -= 0.1
        return EvaluationComponent(
            score=_clamp(score),
            issues=issues,
            recommendations=recommendations,
        )


class ExecutionEvaluator:
    """分析 execution_orchestration.json:成功率 / 重试 / 状态转换合法性。"""

    def evaluate(self, trace: dict) -> EvaluationComponent:
        steps = trace.get("steps") or []
        if not steps:
            return EvaluationComponent(
                score=0.0,
                issues=["无执行步骤"],
                recommendations=["补充执行编排 trace"],
            )
        score = 0.0
        issues: list[str] = []
        recommendations: list[str] = []
        total = len(steps)
        completed = sum(
            1 for step in steps if step.get("status") == "COMPLETED"
        )
        success_rate = completed / total
        score += success_rate * 0.5
        failed = [
            step.get("status")
            for step in steps
            if step.get("status") in ("FAILED", "BLOCKED")
        ]
        if failed:
            issues.append(f"失败/阻断步骤: {len(failed)}")
        retries = sum(
            (step.get("task") or {}).get("retry_count", 0) for step in steps
        )
        if retries:
            issues.append(f"存在重试: {retries} 次")
            score -= 0.05 * retries
        invalid = self._invalid_transitions(steps)
        if invalid:
            issues.append(f"非法状态转换: {len(invalid)} 处")
            recommendations.append("检查执行状态机转换")
        else:
            score += 0.3
        state = trace.get("state") or {}
        if state.get("status") == "COMPLETED":
            score += 0.2
        else:
            issues.append("编排未完成: " + str(state.get("status", "")))
        return EvaluationComponent(
            score=_clamp(score),
            issues=issues,
            recommendations=recommendations,
        )

    @staticmethod
    def _invalid_transitions(steps: list[dict]) -> list[dict]:
        from maple_agent.execution.state_machine import (
            ExecutionStepStatus,
            validate_transition,
        )

        invalid: list[dict] = []
        for step in steps:
            for transition in step.get("transitions") or []:
                try:
                    validate_transition(
                        ExecutionStepStatus(transition["from"]),
                        ExecutionStepStatus(transition["to"]),
                    )
                except Exception:
                    invalid.append(transition)
        return invalid


class ReflectionEvaluator:
    """分析 reflection_trace.json:失败类型 / next_action / replan 判定。"""

    def evaluate(self, trace: dict) -> EvaluationComponent:
        score = 0.4
        issues: list[str] = []
        recommendations: list[str] = []
        analysis = trace.get("analysis") or {}
        success = analysis.get("success") is True
        trigger = trace.get("trigger")
        next_plan = trace.get("next_plan")
        if success and trigger == "NO_ACTION" and next_plan == "continue":
            score += 0.4
        elif (
            not success
            and trigger == "REPLAN_REQUIRED"
            and next_plan == "replan"
        ):
            score += 0.4
        else:
            issues.append(
                f"反思判定不一致: success={success} trigger={trigger} "
                f"next={next_plan}"
            )
            recommendations.append("统一反思结果与重规划触发判定")
        if not success:
            failure_type = analysis.get("failure_type")
            if failure_type:
                score += 0.1
                if not analysis.get("failure_reason"):
                    issues.append("失败类型缺少原因说明")
            else:
                issues.append("失败反思缺少失败类型")
        confidence = analysis.get("confidence", 0)
        if confidence >= 0.5:
            score += 0.1
        else:
            issues.append("反思置信度过低")
        return EvaluationComponent(
            score=_clamp(score),
            issues=issues,
            recommendations=recommendations,
        )


class MemoryEvaluator:
    """分析经验利用:命中率 / 成功经验提升 / 失败经验避错。"""

    def evaluate(
        self,
        decision_trace: dict,
        store: ExperienceStore | None = None,
    ) -> EvaluationComponent:
        score = 0.4
        issues: list[str] = []
        recommendations: list[str] = []
        experience = decision_trace.get("experience")
        retrieved = (
            experience.get("retrieved") if experience is not None else None
        )
        if retrieved:
            score += 0.25
            successes = [r for r in retrieved if r.get("success")]
            failures = [r for r in retrieved if not r.get("success")]
            if successes:
                score += 0.15
            selected = decision_trace.get("selected") or {}
            same_action_failures = [
                r
                for r in failures
                if r.get("action") == selected.get("action")
            ]
            if same_action_failures:
                score -= 0.2
                issues.append("重复选择失败过的动作")
                recommendations.append("应避开失败经验对应的动作")
            elif failures:
                score += 0.1
        else:
            issues.append("未命中历史经验")
            recommendations.append("扩大经验库覆盖当前情境")
        if store is not None:
            total = store.count()
            if total == 0:
                issues.append("经验库为空")
            else:
                score += min(0.1, total * 0.02)
        return EvaluationComponent(
            score=_clamp(score),
            issues=issues,
            recommendations=recommendations,
        )
