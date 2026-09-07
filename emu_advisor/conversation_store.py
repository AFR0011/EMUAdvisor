"""Capability-protected conversation sessions with opt-in disk persistence."""

from __future__ import annotations

import hashlib
import hmac
import html
import json
import os
import secrets
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional


MAX_MESSAGES = 20
SESSION_TTL_S = 1800
DEFAULT_SESSION_STORE_PATH = Path("artifacts") / "chat_sessions.json"
SESSION_ID_BYTES = 16
CAPABILITY_BYTES = 32


def _enabled(name: str) -> bool:
    return os.getenv(name, "").casefold() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class SessionAccess:
    session_id: str
    capability: str


@dataclass
class _Session:
    session_id: str
    capability_hash: str
    messages: List[Mapping[str, str]] = field(default_factory=list)
    language: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)


@dataclass
class SessionInfo:
    session_id: str
    created_at: float
    last_active: float
    message_count: int


class ConversationStore:
    """Store sessions whose public operations require a separate bearer capability."""

    def __init__(self, persist_path: Optional[Path | str] = None, *, persistence_enabled: Optional[bool] = None) -> None:
        import threading

        self._sessions: Dict[str, _Session] = {}
        self._lock = threading.Lock()
        if persistence_enabled is None:
            persistence_enabled = _enabled("EMU_ADVISOR_ENABLE_CHAT_PERSISTENCE")
        configured_path = os.getenv("EMU_ADVISOR_CHAT_STORE_PATH")
        self._persist_path = Path(persist_path or configured_path or DEFAULT_SESSION_STORE_PATH) if persistence_enabled else None
        self._load_from_disk()

    @staticmethod
    def _hash_capability(capability: str) -> str:
        return hashlib.sha256(capability.encode("utf-8")).hexdigest()

    @classmethod
    def _authorized(cls, session: _Session, capability: Optional[str]) -> bool:
        if not capability or len(capability) < 32:
            return False
        return hmac.compare_digest(session.capability_hash, cls._hash_capability(capability))

    def _session_to_dict(self, session: _Session) -> Dict[str, Any]:
        return {
            "session_id": session.session_id,
            "capability_hash": session.capability_hash,
            "messages": list(session.messages[-MAX_MESSAGES:]),
            "language": session.language,
            "created_at": session.created_at,
            "last_active": session.last_active,
        }

    def _session_from_dict(self, payload: Mapping[str, Any]) -> Optional[_Session]:
        session_id = str(payload.get("session_id") or "").strip()
        capability_hash = str(payload.get("capability_hash") or "").strip()
        if not session_id or len(capability_hash) != 64:
            # Legacy sessions intentionally remain on disk but are not loaded into
            # the public capability boundary.
            return None
        raw_messages = payload.get("messages") or []
        messages: List[Mapping[str, str]] = []
        if isinstance(raw_messages, list):
            for item in raw_messages[-MAX_MESSAGES:]:
                if not isinstance(item, Mapping):
                    continue
                role = str(item.get("role") or "").strip()
                text = str(item.get("text") or item.get("content") or "").strip()
                if role in {"user", "assistant", "system"} and text:
                    messages.append({"role": role, "text": text})
        now = time.time()
        return _Session(
            session_id=session_id,
            capability_hash=capability_hash,
            messages=messages,
            language=str(payload.get("language") or "") or None,
            created_at=float(payload.get("created_at") or now),
            last_active=float(payload.get("last_active") or now),
        )

    def _load_from_disk(self) -> None:
        if self._persist_path is None or not self._persist_path.exists():
            return
        try:
            payload = json.loads(self._persist_path.read_text(encoding="utf-8"))
        except Exception:
            return
        if not isinstance(payload, Mapping) or payload.get("version") != 2:
            # Never overwrite or migrate a legacy/private transcript file implicitly.
            self._persist_path = None
            return
        raw_sessions = payload.get("sessions", []) if isinstance(payload, Mapping) else []
        if not isinstance(raw_sessions, list):
            return
        now = time.time()
        for item in raw_sessions:
            if not isinstance(item, Mapping):
                continue
            session = self._session_from_dict(item)
            if session is not None and now - session.last_active <= SESSION_TTL_S:
                self._sessions[session.session_id] = session
        # Opt-in stores are rewritten after load so expired/capability-less legacy
        # entries are removed from the active-format file.
        self._save_to_disk()

    def _save_to_disk(self) -> None:
        if self._persist_path is None:
            return
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "version": 2,
                "saved_at": time.time(),
                "ttl_seconds": SESSION_TTL_S,
                "max_messages": MAX_MESSAGES,
                "sessions": [self._session_to_dict(session) for session in self._sessions.values()],
            }
            tmp_path = self._persist_path.with_suffix(self._persist_path.suffix + ".tmp")
            tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp_path.replace(self._persist_path)
        except Exception:
            return

    def _prune(self) -> bool:
        now = time.time()
        expired = [sid for sid, session in self._sessions.items() if now - session.last_active > SESSION_TTL_S]
        for session_id in expired:
            del self._sessions[session_id]
        return bool(expired)

    def create_session(self) -> SessionAccess:
        with self._lock:
            self._prune()
            while True:
                session_id = secrets.token_urlsafe(SESSION_ID_BYTES)
                if session_id not in self._sessions:
                    break
            capability = secrets.token_urlsafe(CAPABILITY_BYTES)
            self._sessions[session_id] = _Session(
                session_id=session_id,
                capability_hash=self._hash_capability(capability),
            )
            self._save_to_disk()
            return SessionAccess(session_id=session_id, capability=capability)

    def owns_session(self, session_id: Optional[str], capability: Optional[str]) -> bool:
        if not session_id:
            return False
        with self._lock:
            changed = self._prune()
            session = self._sessions.get(session_id)
            allowed = session is not None and self._authorized(session, capability)
            if changed:
                self._save_to_disk()
            return allowed

    def get_session(self, session_id: Optional[str], capability: Optional[str]) -> Optional[Dict[str, Any]]:
        if not session_id:
            return None
        with self._lock:
            changed = self._prune()
            session = self._sessions.get(session_id)
            if session is None or not self._authorized(session, capability):
                if changed:
                    self._save_to_disk()
                return None
            session.last_active = time.time()
            self._save_to_disk()
            return self._public_session(session)

    def get_session_admin(self, session_id: Optional[str]) -> Optional[Dict[str, Any]]:
        if not session_id:
            return None
        with self._lock:
            changed = self._prune()
            session = self._sessions.get(session_id)
            if session is None:
                if changed:
                    self._save_to_disk()
                return None
            return self._public_session(session)

    @staticmethod
    def _public_session(session: _Session) -> Dict[str, Any]:
        return {
            "session_id": session.session_id,
            "messages": list(session.messages),
            "language": session.language,
            "created_at": session.created_at,
            "last_active": session.last_active,
        }

    def add_message(self, session_id: str, capability: str, role: str, text: str) -> bool:
        with self._lock:
            self._prune()
            session = self._sessions.get(session_id)
            if session is None or not self._authorized(session, capability):
                return False
            session.messages.append({"role": role, "text": text})
            session.messages = session.messages[-MAX_MESSAGES:]
            session.last_active = time.time()
            self._save_to_disk()
            return True

    def get_history(self, session_id: str, capability: str, max_exchanges: int = 6) -> List[Mapping[str, str]]:
        session = self.get_session(session_id, capability)
        if session is None:
            return []
        return list(session["messages"][-max_exchanges * 2 :])

    def get_history_admin(self, session_id: str, max_exchanges: int = 6) -> List[Mapping[str, str]]:
        session = self.get_session_admin(session_id)
        if session is None:
            return []
        return list(session["messages"][-max_exchanges * 2 :])

    def prune_expired(self) -> int:
        with self._lock:
            before = len(self._sessions)
            changed = self._prune()
            if changed:
                self._save_to_disk()
            return before - len(self._sessions)

    def list_sessions(self) -> List[SessionInfo]:
        with self._lock:
            changed = self._prune()
            sessions = [
                SessionInfo(
                    session_id=session.session_id,
                    created_at=session.created_at,
                    last_active=session.last_active,
                    message_count=len(session.messages),
                )
                for session in self._sessions.values()
            ]
            sessions.sort(key=lambda session: session.last_active, reverse=True)
            if changed:
                self._save_to_disk()
            return sessions

    def clear_session(self, session_id: str, capability: str) -> bool:
        with self._lock:
            self._prune()
            session = self._sessions.get(session_id)
            if session is None or not self._authorized(session, capability):
                return False
            session.messages = []
            session.last_active = time.time()
            self._save_to_disk()
            return True

    def export_session(self, session_id: str, capability: str, format: str = "markdown") -> Optional[str]:
        with self._lock:
            self._prune()
            session = self._sessions.get(session_id)
            if session is None or not self._authorized(session, capability):
                return None
            export_format = format.lower().strip()
            if export_format not in {"markdown", "html"}:
                export_format = "markdown"
            if export_format == "markdown":
                messages = []
                for message in session.messages:
                    role = str(message.get("role", "unknown")).title()
                    messages.append(f"**{role}:**\n{message.get('text', '')}")
                return "# Chat transcript\n\n" + "\n\n".join(messages) + "\n"
            blocks = []
            for message in session.messages:
                role = html.escape(str(message.get("role", "unknown")))
                text = html.escape(str(message.get("text", ""))).replace("\n", "<br>")
                blocks.append(f'<div class="message"><strong>{role.title()}</strong><div>{text}</div></div>')
            return "<!doctype html><html><head><meta charset=\"utf-8\"><title>Chat transcript</title></head><body>" + "\n".join(blocks) + "</body></html>"


_store: Optional[ConversationStore] = None


def get_store() -> ConversationStore:
    global _store
    if _store is None:
        _store = ConversationStore()
    return _store


def reset_store() -> None:
    """Reset process-local state; intended for isolated application/test startup."""
    global _store
    _store = None
