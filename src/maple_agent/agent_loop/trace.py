"""AgentLoopTrace:统一闭环 Replay(只读审计)。"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field

from maple_agent.architecture import AGENT_VERSION, TRACE_SCHEMA_VERSION


class AgentLoopStage(BaseModel):
    """单个阶段记录。"""

    stage: str
    status: str = ""


class AgentLoopTrace(BaseModel):
    """统一闭环 trace。"""

    schema_version: str = TRACE_SCHEMA_VERSION
    trace_id: str = ""
    agent_version: str = AGENT_VERSION
    stages: list[AgentLoopStage] = Field(default_factory=list)
    final_status: str = ""


class AgentLoopTraceWriter:
    """把 trace 写入 sessions/<trace_id>/agent_loop_trace.json。"""

    def __init__(self, sessions_dir: str | Path = "sessions") -> None:
        self.sessions_dir = Path(sessions_dir)

    def write(self, trace: AgentLoopTrace) -> None:
        if not trace.trace_id:
            return
        directory = self.sessions_dir / trace.trace_id
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "agent_loop_trace.json").write_text(
            json.dumps(
                trace.model_dump(mode="json"),
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
