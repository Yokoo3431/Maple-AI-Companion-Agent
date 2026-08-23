"""Session bookkeeping without raw observation persistence."""

from __future__ import annotations

from maple_agent.companion_runtime.models import CompanionSession, CompanionSnapshot


class CompanionSessionStore:
    """Maintain a sanitized session summary while the reducer owns memory."""

    def __init__(self, session: CompanionSession | None = None) -> None:
        self.session = session or CompanionSession(session_id="companion-session")

    def record(
        self,
        snapshot: CompanionSnapshot,
        *,
        state_id: str,
    ) -> CompanionSession:
        self.session.current_snapshot = snapshot
        self.session.snapshot_count += 1
        self.session.history_reference_ids.extend(
            [snapshot.observation_id, state_id]
        )
        self.session.history_reference_ids = list(
            dict.fromkeys(self.session.history_reference_ids)
        )
        return self.session
