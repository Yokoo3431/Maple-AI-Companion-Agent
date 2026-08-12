"""Action Proposal 数据模型(Phase 12-C,动作建议参考,不执行)。"""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, Field


class ActionType(StrEnum):
    """语义动作类型(不是执行动作)。"""

    OBSERVE = "OBSERVE"
    NAVIGATE = "NAVIGATE"
    INTERACT = "INTERACT"
    COMBAT = "COMBAT"
    COLLECT = "COLLECT"
    VERIFY = "VERIFY"
    WAIT = "WAIT"


class ActionProposalReference(BaseModel):
    """动作建议参考(Reference,不是 Command)。"""

    action_id: str
    action_type: ActionType
    source_behavior: str = ""
    target_reference: str = ""
    parameters_reference: dict = Field(default_factory=dict)
    confidence: float = Field(default=0.0, ge=0, le=1)
    validation: str = ""
