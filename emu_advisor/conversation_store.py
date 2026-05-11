"""In-memory conversation session store with TTL and message cap."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional


MAX_MESSAGES = 20
SESSION_TTL_S = 1800  # 30 minutes


@dataclass
class _Session:
    session_id: str
    messages: List[Mapping[str, str]] = field(default_factory=list)
    language: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)


class ConversationStore:
    def __init__(self) -> None:
        import threading

        self._sessions: Dict[str, _Session] = {}
        self._lock = threading.Lock()

    def _prune(self) -> None:
        now = time.time()
        expired = [sid for sid, s in self._sessions.items() if now - s.last_active > SESSION_TTL_S]
        for sid in expired:
            del self._sessions[sid]

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            self._prune()
            session = self._sessions.get(session_id)
            if session is None:
                return None
            session.last_active = time.time()
            return {
                "session_id": session.session_id,
                "messages": list(session.messages),
                "language": session.language,
                "created_at": session.created_at,
                "last_active": session.last_active,
            }

    def create_session(self, session_id: Optional[str] = None) -> str:
        with self._lock:
            self._prune()
            if session_id is None:
                session_id = uuid.uuid4().hex
            if session_id not in self._sessions:
                self._sessions[session_id] = _Session(session_id=session_id)
            self._sessions[session_id].last_active = time.time()
            return session_id

    def add_message(self, session_id: str, role: str, text: str) -> None:
        with self._lock:
            self._prune()
            session = self._sessions.get(session_id)
            if session is None:
                session = _Session(session_id=session_id)
                self._sessions[session_id] = session
            session.messages.append({"role": role, "text": text})
            if len(session.messages) > MAX_MESSAGES:
                session.messages = session.messages[-MAX_MESSAGES:]
            session.last_active = time.time()

    def get_history(self, session_id: str, max_exchanges: int = 6) -> List[Mapping[str, str]]:
        with self._lock:
            self._prune()
            session = self._sessions.get(session_id)
            if session is None:
                return []
            max_msgs = max_exchanges * 2
            return list(session.messages[-max_msgs:])

    def prune_expired(self) -> int:
        with self._lock:
            before = len(self._sessions)
            self._prune()
            return before - len(self._sessions)


_store: Optional[ConversationStore] = None


def get_store() -> ConversationStore:
    global _store
    if _store is None:
        _store = ConversationStore()
    return _store
