"""Conversation session store with TTL, message cap, and optional disk persistence."""

from __future__ import annotations

import html
import json
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional


MAX_MESSAGES = 20
SESSION_TTL_S = 1800  # 30 minutes
DEFAULT_SESSION_STORE_PATH = Path("artifacts") / "chat_sessions.json"


def _persistence_disabled() -> bool:
    return os.getenv("EMU_ADVISOR_DISABLE_CHAT_PERSISTENCE", "").casefold() in {"1", "true", "yes", "on"}


@dataclass
class _Session:
    session_id: str
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
    last_user_message: Optional[str] = None


class ConversationStore:
    def __init__(self, persist_path: Optional[Path | str] = None) -> None:
        import threading

        self._sessions: Dict[str, _Session] = {}
        self._lock = threading.Lock()
        if _persistence_disabled():
            self._persist_path: Optional[Path] = None
        else:
            configured_path = os.getenv("EMU_ADVISOR_CHAT_STORE_PATH")
            self._persist_path = Path(persist_path or configured_path or DEFAULT_SESSION_STORE_PATH)
        self._load_from_disk()

    def _session_to_dict(self, session: _Session) -> Dict[str, Any]:
        return {
            "session_id": session.session_id,
            "messages": list(session.messages[-MAX_MESSAGES:]),
            "language": session.language,
            "created_at": session.created_at,
            "last_active": session.last_active,
        }

    def _session_from_dict(self, payload: Mapping[str, Any]) -> Optional[_Session]:
        session_id = str(payload.get("session_id") or "").strip()
        if not session_id:
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
        raw_sessions = payload.get("sessions", []) if isinstance(payload, Mapping) else []
        if not isinstance(raw_sessions, list):
            return
        now = time.time()
        for item in raw_sessions:
            if not isinstance(item, Mapping):
                continue
            session = self._session_from_dict(item)
            if session is None:
                continue
            if now - session.last_active <= SESSION_TTL_S:
                self._sessions[session.session_id] = session

    def _save_to_disk(self) -> None:
        if self._persist_path is None:
            return
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "version": 1,
                "saved_at": time.time(),
                "ttl_seconds": SESSION_TTL_S,
                "max_messages": MAX_MESSAGES,
                "sessions": [self._session_to_dict(session) for session in self._sessions.values()],
            }
            tmp_path = self._persist_path.with_suffix(self._persist_path.suffix + ".tmp")
            tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp_path.replace(self._persist_path)
        except Exception:
            # Chat persistence must never break the main assistant path.
            return

    def _prune(self) -> bool:
        now = time.time()
        expired = [sid for sid, s in self._sessions.items() if now - s.last_active > SESSION_TTL_S]
        for sid in expired:
            del self._sessions[sid]
        return bool(expired)

    def get_session(self, session_id: Optional[str]) -> Optional[Dict[str, Any]]:
        if not session_id:
            return None
        with self._lock:
            changed = self._prune()
            session = self._sessions.get(session_id)
            if session is None:
                if changed:
                    self._save_to_disk()
                return None
            session.last_active = time.time()
            self._save_to_disk()
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
            self._save_to_disk()
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
            self._save_to_disk()

    def get_history(self, session_id: str, max_exchanges: int = 6) -> List[Mapping[str, str]]:
        with self._lock:
            changed = self._prune()
            session = self._sessions.get(session_id)
            if session is None:
                if changed:
                    self._save_to_disk()
                return []
            max_msgs = max_exchanges * 2
            session.last_active = time.time()
            self._save_to_disk()
            return list(session.messages[-max_msgs:])

    def prune_expired(self) -> int:
        with self._lock:
            before = len(self._sessions)
            changed = self._prune()
            if changed:
                self._save_to_disk()
            return before - len(self._sessions)

    def list_sessions(self) -> List[SessionInfo]:
        """Return list of active sessions with metadata."""
        with self._lock:
            changed = self._prune()
            sessions = []
            for sid, session in self._sessions.items():
                last_user_msg = None
                for msg in reversed(session.messages):
                    if msg.get("role") == "user":
                        last_user_msg = msg.get("text")
                        break
                sessions.append(SessionInfo(
                    session_id=session.session_id,
                    created_at=session.created_at,
                    last_active=session.last_active,
                    message_count=len(session.messages),
                    last_user_message=last_user_msg,
                ))
            # Sort by last active descending
            sessions.sort(key=lambda s: s.last_active, reverse=True)
            if changed:
                self._save_to_disk()
            return sessions

    def clear_session(self, session_id: str) -> bool:
        """Clear all messages in a session, keeping the session active."""
        with self._lock:
            self._prune()
            session = self._sessions.get(session_id)
            if session is None:
                return False
            session.messages = []
            session.last_active = time.time()
            self._save_to_disk()
            return True

    def export_session(self, session_id: str, format: str = "markdown") -> Optional[str]:
        """Export session history to specified format."""
        with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None

            format = format.lower().strip()
            if format not in ("markdown", "html"):
                format = "markdown"

            messages_text = []
            for msg in session.messages:
                role = msg.get("role", "unknown")
                text = msg.get("text", "")
                if role == "user":
                    messages_text.append(f"**User:**\n{text}")
                elif role == "assistant":
                    messages_text.append(f"**Assistant:**\n{text}")
                else:
                    messages_text.append(f"**{role}:**\n{text}")

            content = "\n\n".join(messages_text)

            if format == "markdown":
                return f"""# Chat Session: {session_id}

**Started:** {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(session.created_at))}
**Last Active:** {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(session.last_active))}
**Message Count:** {len(session.messages)}

---

## Conversation

{content}
"""
            timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(session.created_at))
            active = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(session.last_active))
            message_blocks = []
            for msg in session.messages:
                role = html.escape(str(msg.get("role", "unknown")))
                text = html.escape(str(msg.get("text", ""))).replace("\n", "<br>")
                css_role = "user" if role == "user" else "assistant"
                message_blocks.append(
                    f'<div class="message {css_role}"><div class="role">{role.title()}</div><div>{text}</div></div>'
                )
            html_messages = "\n".join(message_blocks)
            return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>Chat Session: {html.escape(session_id)}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }}
    .header {{ border-bottom: 1px solid #ddd; padding-bottom: 16px; margin-bottom: 20px; }}
    .header h1 {{ margin: 0 0 8px 0; font-size: 1.2em; }}
    .meta {{ color: #666; font-size: 0.9em; }}
    .message {{ margin-bottom: 16px; padding: 12px 16px; border-radius: 8px; }}
    .user {{ background: #0b4d79; color: white; }}
    .assistant {{ background: #f7f8fb; }}
    .role {{ font-weight: bold; margin-bottom: 4px; }}
  </style>
</head>
<body>
  <div class="header">
    <h1>Chat Session: {html.escape(session_id)}</h1>
    <div class="meta">Started: {html.escape(timestamp)} | Last Active: {html.escape(active)} | {len(session.messages)} messages</div>
  </div>
  <div class="messages">
{html_messages}
  </div>
</body>
</html>"""


_store: Optional[ConversationStore] = None


def get_store() -> ConversationStore:
    global _store
    if _store is None:
        _store = ConversationStore()
    return _store
