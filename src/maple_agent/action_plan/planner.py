"""ActionPlanner:DecisionResult → 结构化 ActionPlan(只读规格,不执行)。"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING

from maple_agent.action_plan.models import (
    ActionPlan,
    ActionPlanStatus,
    ActionStep,
)
from maple_agent.action_plan.validator import (
    ActionPlanValidationResult,
    ActionPlanValidator,
)
from maple_agent.context.models import KnowledgeState
from maple_agent.fusion.models import WorldState
from maple_agent.logging_setup import TraceContext, new_id

if TYPE_CHECKING:
    from maple_agent.decision.models import DecisionResult

logger = logging.getLogger("maple_agent.action_plan")

_ACTION_TEMPLATES: dict[str, list[tuple[str, str, str]]] = {
    "TALK": [
        ("确认目标 NPC 位于当前地图", "屏幕/地图中可见目标 NPC", "目标 NPC 已识别"),
        ("与目标 NPC 对话", "对话窗口出现", "对话已发起"),
        ("检查对话结果(接取/提交任务)", "对话结果文本已获取", "任务状态符合预期"),
    ],
    "COLLECT": [
        ("确认目标物品来源", "目标物品/来源可见", "来源已识别"),
        ("执行收集动作", "收集提示出现", "物品数量变化"),
        ("检查背包物品数量", "背包状态可观察", "数量满足预期"),
    ],
    "DEFEAT": [
        ("确认目标怪物刷新", "目标怪物可见", "怪物已识别"),
        ("执行战斗动作", "战斗状态可见", "怪物血量变化"),
        ("检查击败计数", "击杀提示出现", "计数满足预期"),
    ],
    "DELIVER": [
        ("确认交付 NPC 位置", "目标 NPC 可见", "NPC 已识别"),
        ("执行交付动作", "交付界面出现", "交付完成"),
        ("检查任务进度", "任务面板状态可读", "进度更新"),
    ],
    "COMPLETE": [
        ("确认任务完成条件", "任务面板可读", "条件已满足"),
        ("提交完成任务", "完成提示出现", "任务状态变为完成"),
        ("检查奖励", "奖励提示出现", "奖励已到账"),
    ],
    "MOVE_HINT": [
        ("确认目标地图位置", "小地图/地图名可读", "目标地图已识别"),
        ("规划路径", "路径信息可用", "路径已规划"),
        ("移动到目标地图", "地图名切换", "已到达目标地图"),
    ],
    "ANALYZE": [
        ("采集当前观察", "屏幕帧已获取", "帧有效"),
        ("分析上下文", "上下文已构建", "分析结论生成"),
    ],
    "OBSERVE": [
        ("截图当前窗口", "屏幕帧已获取", "帧有效"),
        ("运行 OCR", "OCR 结果已返回", "文本已提取"),
        ("更新世界状态", "融合结果已生成", "世界状态已更新"),
    ],
    "QUERY_KNOWLEDGE": [
        ("构造知识查询", "查询文本已准备", "查询有效"),
        ("检索知识库", "检索结果已返回", "候选已生成"),
        ("输出匹配实体", "匹配结果可用", "实体已确认"),
    ],
    "WAIT": [
        ("记录等待原因", "原因已记录", "原因明确"),
        ("定期复查状态", "状态可观察", "等待条件满足"),
    ],
    "PAUSE": [
        ("记录暂停原因", "原因已记录", "原因明确"),
        ("等待用户确认", "用户输入可用", "已获得确认"),
    ],
}


class ActionPlanner:
    """把 DecisionResult 展开为结构化 ActionPlan;禁止执行。"""

    def __init__(
        self,
        *,
        validator: ActionPlanValidator | None = None,
        sessions_dir: str | Path = "sessions",
    ) -> None:
        self.validator = validator or ActionPlanValidator()
        self.sessions_dir = Path(sessions_dir)
        self.last_plan: ActionPlan | None = None
        self.last_validation: ActionPlanValidationResult | None = None

    def plan(
        self,
        decision: DecisionResult,
        *,
        world_state: WorldState | None = None,
        knowledge_state: KnowledgeState | None = None,
        goal_id: str | None = None,
        trace_id: str | None = None,
    ) -> ActionPlan:
        """输入 DecisionResult + 世界/知识状态,输出 ActionPlan(只读)。"""
        with TraceContext(trace_id=trace_id) as trace:
            selected = decision.selected_option
            plan_id = new_id()
            action = selected.action if selected is not None else ""
            target = selected.target if selected is not None else ""
            confidence = (
                selected.confidence if selected is not None else 0.0
            )
            prerequisites = self._prerequisites(
                decision,
                world_state,
                knowledge_state,
            )
            plan = ActionPlan(
                plan_id=plan_id,
                decision_id=(
                    selected.decision_id if selected is not None else ""
                ),
                goal_id=goal_id or "",
                action=action,
                target=target,
                prerequisites=prerequisites,
                validation_conditions=self._validation_conditions(
                    action,
                    target,
                ),
                expected_result=(
                    selected.expected_result if selected is not None else ""
                ),
                confidence=confidence,
                status=ActionPlanStatus.VALIDATING,
                steps=self._steps(plan_id, action, target),
                trace_id=trace.trace_id,
            )
            validation = self.validator.validate(plan)
            plan = plan.model_copy(
                update={
                    "status": validation.status,
                    "validation_conditions": self._validation_conditions(
                        action,
                        target,
                        validation=validation,
                    ),
                }
            )
            self.last_plan = plan
            self.last_validation = validation
            self._write_replay(
                trace.trace_id,
                decision,
                plan,
                validation,
            )
            logger.info(
                "action plan: action=%s status=%s steps=%d valid=%s",
                plan.action or "-",
                plan.status.value,
                len(plan.steps),
                validation.valid,
            )
            return plan

    def _steps(
        self,
        plan_id: str,
        action: str,
        target: str,
    ) -> list[ActionStep]:
        template = _ACTION_TEMPLATES.get(action, [])
        return [
            ActionStep(
                step_id=f"{plan_id}-step-{index + 1}",
                description=description,
                required_observation=required_observation,
                success_condition=success_condition,
            )
            for index, (description, required_observation, success_condition)
            in enumerate(template)
        ] or [
            ActionStep(
                step_id=f"{plan_id}-step-1",
                description=f"复查 {action or '未知'} 动作上下文",
                required_observation="当前状态可观察",
                success_condition="上下文已确认",
            )
        ]

    @staticmethod
    def _prerequisites(
        decision: DecisionResult,
        world_state: WorldState | None,
        knowledge_state: KnowledgeState | None,
    ) -> list[str]:
        """从当前世界/知识状态生成前置条件;缺失项标记为 缺失: 前缀。"""
        items: list[str] = []
        if decision.selected_option is None:
            items.append("缺失: 选中决策")
        if world_state is None:
            items.append("缺失: 世界状态")
        elif world_state.current_map is None:
            items.append("缺失: 地图信息")
        else:
            items.append(f"地图: {world_state.current_map.name}")
        if knowledge_state is None:
            items.append("缺失: 知识状态")
        elif knowledge_state.confidence < 0.6:
            items.append("缺失: 知识置信度")
        else:
            items.append(
                "知识: "
                + (knowledge_state.selection_reason or "已匹配")
            )
        selected = decision.selected_option
        if selected is not None and selected.target:
            items.append(f"目标: {selected.target}")
        return items

    @staticmethod
    def _validation_conditions(
        action: str,
        target: str,
        *,
        validation: ActionPlanValidationResult | None = None,
    ) -> list[str]:
        conditions = [
            f"观察确认: {target or '目标'} 可达",
            "执行后复查世界状态",
            "置信度 >= 0.6",
        ]
        if validation is not None and not validation.valid:
            conditions.append("校验失败: " + "；".join(validation.errors))
        return conditions

    def _write_replay(
        self,
        trace_id: str,
        decision: DecisionResult,
        plan: ActionPlan,
        validation: ActionPlanValidationResult,
    ) -> None:
        directory = self.sessions_dir / trace_id
        directory.mkdir(parents=True, exist_ok=True)
        payload = {
            "trace_id": trace_id,
            "decision_input": decision.model_dump(mode="json"),
            "generated_steps": [
                step.model_dump(mode="json") for step in plan.steps
            ],
            "prerequisites": plan.prerequisites,
            "validation_result": validation.model_dump(mode="json"),
            "plan": plan.model_dump(mode="json"),
        }
        (directory / "action_plan_trace.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
