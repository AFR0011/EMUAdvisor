"""Privacy-preserving query audit logging."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from statistics import median
from typing import Any, Dict, Iterable, Optional


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


def summarize_audit_log(path: Path) -> Dict[str, Any]:
    events = list(_read_events(path))
    latencies = [int(event.get("latency_ms", 0)) for event in events if isinstance(event.get("latency_ms"), int)]
    answer_modes: Dict[str, int] = {}
    event_types: Dict[str, int] = {}
    language_counts: Dict[str, int] = {}
    refusal_count = 0
    for event in events:
        answer_mode = str(event.get("answer_mode") or "unknown")
        event_type = str(event.get("event_type") or "unknown")
        route = event.get("route") if isinstance(event.get("route"), dict) else {}
        language = str(route.get("query_language") or "unknown")
        answer_modes[answer_mode] = answer_modes.get(answer_mode, 0) + 1
        event_types[event_type] = event_types.get(event_type, 0) + 1
        language_counts[language] = language_counts.get(language, 0) + 1
        if route.get("in_scope") is False:
            refusal_count += 1
    return {
        "available": path.exists(),
        "path": str(path),
        "events": len(events),
        "event_types": event_types,
        "answer_modes": answer_modes,
        "languages": language_counts,
        "out_of_scope_or_refusal_routes": refusal_count,
        "latency_p50_ms": _percentile(latencies, 0.50),
        "latency_p95_ms": _percentile(latencies, 0.95),
    }


def _read_events(path: Path) -> Iterable[Dict[str, Any]]:
    if not path.exists():
        return []
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            events.append({"event_type": "parse_error", "latency_ms": 0})
    return events


def _percentile(values: list[int], ratio: float) -> Optional[int]:
    if not values:
        return None
    ordered = sorted(values)
    if ratio == 0.50:
        return int(median(ordered))
    index = min(len(ordered) - 1, max(0, int(round((len(ordered) - 1) * ratio))))
    return int(ordered[index])
