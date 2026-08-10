"""SandboxPolicy:限制允许进入沙箱的动作白名单。"""

from __future__ import annotations


class SandboxPolicy:
    """沙箱动作策略;只允许语义观察/对话类动作。"""

    ALLOWED_ACTIONS = frozenset({"TALK", "OBSERVE", "QUERY_KNOWLEDGE"})
    BLOCKED_ACTIONS = frozenset({"UNKNOWN", "DIRECT_INPUT", "RAW_CONTROL"})

    def allows(self, action: str) -> bool:
        return action.upper() in self.ALLOWED_ACTIONS

    def block_reason(self, action: str) -> str:
        if action.upper() in self.BLOCKED_ACTIONS:
            return f"禁止动作: {action}"
        return f"动作不在沙箱白名单: {action}"
