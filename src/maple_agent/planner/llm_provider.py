"""LLM Planner Adapter:接入现有 LLMProvider 生成结构化 PlanResult(Phase 1.8-A)。"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from maple_agent.logging_setup import TraceContext, new_id
from maple_agent.planner.action import ALLOWED_ACTIONS
from maple_agent.planner.models import PlannerInput, PlanResult, PlanStep
from maple_agent.planner.validator import PlanValidationError, PlanValidator
from maple_agent.providers.llm import LLMProvider, LLMRequest

logger = logging.getLogger("maple_agent.planner")


class LLMPlannerProvider:
    """基于 LLMProvider 的 Planner:仅生成结构化 PlanResult,不执行任何动作。"""

    def __init__(
        self,
        llm: LLMProvider,
        *,
        sessions_dir: str | Path = "sessions",
        validator: PlanValidator | None = None,
    ) -> None:
        self.llm = llm
        self.sessions_dir = Path(sessions_dir)
        self.validator = validator or PlanValidator()
        self.last_result: PlanResult | None = None
        self.last_error: str | None = None
        self.call_count = 0

    def plan(self, context: PlannerInput) -> PlanResult:
        self.call_count += 1
        self.last_error = None
        with TraceContext(trace_id=context.trace_id):
            prompt = self._build_prompt(context)
            logger.info("llm planner plan start")
            try:
                reply = self.llm.complete(
                    LLMRequest(prompt=prompt),
                    trace_id=context.trace_id,
                )
                result = self._parse(reply.text, context)
                self.validator.validate(result, constraints=context.constraints)
            except Exception as exc:
                self.last_error = str(exc)
                logger.error("llm planner failed: %s", exc)
                raise
            self.last_result = result
            self._write_replay(context, result)
            logger.info("llm planner plan ok: steps=%d", len(result.steps))
            return result

    def _build_prompt(self, context: PlannerInput) -> str:
        ctx = context.context
        world = ctx.world_state
        current_map = world.current_map.name if world and world.current_map else "未知"
        goals = " | ".join(goal.description for goal in context.goals) or "-"
        constraints = (
            " | ".join(f"{item.kind}={item.value}" for item in context.constraints) or "-"
        )
        return "\n".join(
            [
                "你是 Maple AI Companion Agent 的规划器。只允许输出 JSON,禁止输出其他文字。",
                f"允许的动作: {', '.join(sorted(ALLOWED_ACTIONS))}",
                f"运行时状态: {ctx.runtime_state}",
                f"知识档案: {ctx.knowledge_profile or '-'}",
                f"画面摘要: {ctx.vision_summary or '-'}",
                f"当前地图: {current_map}",
                f"目标: {goals}",
                f"约束: {constraints}",
                '输出 JSON: {"plan_id":"","summary":"","confidence":0.0,'
                '"steps":[{"step_id":"s1","action":"observe","target":"","params":{},'
                '"depends_on":[],"expected_outcome":""}]}',
            ]
        )

    def _parse(self, text: str, context: PlannerInput) -> PlanResult:
        data = self._extract_json(text)
        steps = [
            PlanStep(
                step_id=str(item.get("step_id", f"s{index + 1}")),
                action=str(item.get("action", "")),
                target=str(item.get("target", "")),
                params={str(k): str(v) for k, v in (item.get("params") or {}).items()},
                depends_on=[str(dep) for dep in (item.get("depends_on") or [])],
                expected_outcome=str(item.get("expected_outcome", "")),
            )
            for index, item in enumerate(data.get("steps") or [])
        ]
        return PlanResult(
            plan_id=str(data.get("plan_id") or new_id()),
            goal_id=context.goals[0].goal_id if context.goals else "",
            steps=steps,
            summary=str(data.get("summary", "")),
            confidence=float(data.get("confidence", 0.0)),
            trace_id=context.trace_id,
        )

    def _extract_json(self, text: str) -> dict:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise PlanValidationError("LLM 输出缺少 JSON 对象")
        try:
            data = json.loads(text[start : end + 1])
        except json.JSONDecodeError as exc:
            raise PlanValidationError(f"LLM 输出 JSON 解析失败: {exc}") from exc
        if not isinstance(data, dict):
            raise PlanValidationError("LLM 输出不是 JSON 对象")
        return data

    def _write_replay(self, planner_input: PlannerInput, result: PlanResult) -> None:
        trace_id = planner_input.trace_id or result.trace_id
        if not trace_id:
            return
        directory = self.sessions_dir / trace_id
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "planner_input.json").write_text(
            json.dumps(planner_input.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        (directory / "planner_result.json").write_text(
            json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
