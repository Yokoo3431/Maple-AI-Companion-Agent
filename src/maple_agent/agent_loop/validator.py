"""AgentLoopValidator:阶段顺序 / 确认门控 / 令牌 / Mock Only / Trace 完整性。"""

from __future__ import annotations

from pydantic import BaseModel, Field

from maple_agent.agent_loop.models import AgentLoopContext
from maple_agent.agent_loop.trace import AgentLoopTrace


class AgentLoopValidationResult(BaseModel):
    """闭环校验结果。"""

    valid: bool
    status: str
    issues: list[str] = Field(default_factory=list)


class AgentLoopValidator:
    """校验闭环合法性;只读判断。"""

    VALID_STAGES = (
        "observation",
        "vision_evaluation",
        "knowledge",
        "decision",
        "planning",
        "confirmation",
        "sandbox",
        "reflection",
        "evaluation",
    )

    def validate(
        self,
        context: AgentLoopContext,
        trace: AgentLoopTrace | None = None,
    ) -> AgentLoopValidationResult:
        issues: list[str] = []
        if trace is not None and trace.stages:
            index = -1
            for stage in trace.stages:
                if stage.stage not in self.VALID_STAGES:
                    issues.append(f"未知阶段: {stage.stage}")
                    continue
                current = self.VALID_STAGES.index(stage.stage)
                if current <= index:
                    issues.append(f"阶段顺序非法: {stage.stage}")
                index = current
        if context.sandbox_result is not None:
            if context.confirmation_result is None:
                issues.append("禁止跳过 Human Confirmation")
            if context.permission_token is None:
                issues.append("Sandbox 缺少 PermissionToken")
            if context.sandbox_result.mode != "MOCK_ONLY":
                issues.append("Sandbox 模式非 MOCK_ONLY")
        if context.sandbox_result is None and trace is not None:
            final = trace.final_status
            if final == "COMPLETED":
                issues.append("Trace 不完整: 缺少 sandbox 阶段")
        required = {
            "observation_state": context.observation_state,
            "vision_result": context.vision_result,
            "decision_result": context.decision_result,
            "action_plan": context.action_plan,
            "confirmation_result": context.confirmation_result,
        }
        for name, value in required.items():
            if value is None:
                issues.append(f"Trace 不完整: 缺少 {name}")
        valid = not issues
        return AgentLoopValidationResult(
            valid=valid,
            status="VALID" if valid else "BLOCKED",
            issues=issues,
        )
