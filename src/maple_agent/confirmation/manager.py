"""ConfirmationManager:创建 / 批准 / 拒绝 / 过期 / Replay(禁止调用 executor)。"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from maple_agent.confirmation.models import (
    ConfirmationRequest,
    ConfirmationStatus,
    PermissionToken,
)
from maple_agent.logging_setup import new_id


class ConfirmationError(RuntimeError):
    """确认流程错误。"""


class ConfirmationManager:
    """人工确认生命周期管理;不接触任何执行器。"""

    def __init__(
        self,
        *,
        sessions_dir: str | Path = "sessions",
        ttl_seconds: int = 300,
    ) -> None:
        self.sessions_dir = Path(sessions_dir)
        self.ttl_seconds = ttl_seconds
        self._requests: dict[str, ConfirmationRequest] = {}
        self._tokens: dict[str, PermissionToken] = {}
        self.last_request: ConfirmationRequest | None = None
        self.last_token: PermissionToken | None = None

    def create(self, request: ConfirmationRequest) -> ConfirmationRequest:
        self._requests[request.confirmation_id] = request
        self.last_request = request
        return request

    def approve(self, confirmation_id: str) -> PermissionToken:
        request = self._require(confirmation_id)
        if request.status is not ConfirmationStatus.PENDING:
            raise ConfirmationError(
                f"确认状态不允许批准: {request.status.value}"
            )
        request.status = ConfirmationStatus.APPROVED
        token = PermissionToken(
            token_id=new_id(),
            confirmation_id=confirmation_id,
            approved=True,
            scope=f"{request.action}:{request.target}".strip(":"),
            expires_at=datetime.now(UTC)
            + timedelta(seconds=self.ttl_seconds),
        )
        self._tokens[token.token_id] = token
        self.last_token = token
        self._save_trace(request, token)
        return token

    def reject(self, confirmation_id: str) -> ConfirmationRequest:
        request = self._require(confirmation_id)
        if request.status is not ConfirmationStatus.PENDING:
            raise ConfirmationError(
                f"确认状态不允许拒绝: {request.status.value}"
            )
        request.status = ConfirmationStatus.REJECTED
        self._save_trace(request, None)
        return request

    def expire(self, confirmation_id: str) -> ConfirmationRequest:
        request = self._require(confirmation_id)
        request.status = ConfirmationStatus.EXPIRED
        self._save_trace(request, None)
        return request

    def get(self, confirmation_id: str) -> ConfirmationRequest | None:
        return self._requests.get(confirmation_id)

    def _require(self, confirmation_id: str) -> ConfirmationRequest:
        request = self._requests.get(confirmation_id)
        if request is None:
            raise ConfirmationError(
                f"确认请求不存在: {confirmation_id}"
            )
        return request

    def _save_trace(
        self,
        request: ConfirmationRequest,
        token: PermissionToken | None,
    ) -> None:
        if not request.trace_id:
            return
        directory = self.sessions_dir / request.trace_id
        directory.mkdir(parents=True, exist_ok=True)
        payload = {
            "confirmation_id": request.confirmation_id,
            "action": request.action,
            "target": request.target,
            "vision_score": request.vision_score,
            "risk": request.risk_level,
            "status": request.status.value,
            "permission": "issued" if token is not None else "none",
            "token": (
                token.model_dump(mode="json") if token is not None else None
            ),
            "reason": request.reason,
        }
        (directory / "confirmation_trace.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
