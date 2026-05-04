"""Privacy-preserving query audit logging."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class AuditEvent:
    event_type: str
    query: str
    session_id: Optional[str]
    route: Dict[str, Any]
    answer_mode: str
    latency_ms: int
    citation_ids: list[str]


class AuditLogger:
    def __init__(self, path: Path, *, salt: str = "emu-advisor-local", max_bytes: int = 1_000_000) -> None:
        self.path = path
        self.salt = salt
        self.max_bytes = max_bytes

    def log(self, event: AuditEvent) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._rotate_if_needed()
        payload = {
            "created_at": datetime.now(timezone.utc).isoformat(),
            "event_type": event.event_type,
            "query": event.query,
            "session_hash": self._hash_session(event.session_id),
            "route": event.route,
            "answer_mode": event.answer_mode,
            "latency_ms": event.latency_ms,
            "citation_ids": event.citation_ids,
        }
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True) + "\n")

    def _hash_session(self, session_id: Optional[str]) -> Optional[str]:
        if not session_id:
            return None
        return hashlib.sha256((self.salt + session_id).encode("utf-8")).hexdigest()

    def _rotate_if_needed(self) -> None:
        if not self.path.exists() or self.path.stat().st_size < self.max_bytes:
            return
        rotated = self.path.with_suffix(self.path.suffix + ".1")
        if rotated.exists():
            rotated.unlink()
        self.path.rename(rotated)
