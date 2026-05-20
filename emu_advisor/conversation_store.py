"""In-memory conversation session store with TTL and message cap."""

from __future__ import annotations

import html
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


@dataclass
class SessionInfo:
    session_id: str
    created_at: float
    last_active: float
    message_count: int
    last_user_message: Optional[str] = None


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

    def list_sessions(self) -> List[SessionInfo]:
        """Return list of active sessions with metadata."""
        with self._lock:
            self._prune()
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
            else:  # HTML
                timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(session.created_at))
                active = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(session.last_active))
                html_content = f"""<!DOCTYPE html>
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
    .user {{ background: #0b4d79; color: white; align-self: flex-end; }}
    .assistant {{ background: #f7f8fb; align-self: flex-start; }}
    .role {{ font-weight: bold; margin-bottom: 4px; }}
  </style>
</head>
<body>
  <div class="header">
    <h1>Chat Session: {html.escape(session_id)}</h1>
    <div class="meta">Started: {html.escape(timestamp)} | Last Active: {html.escape(active)} | {len(session.messages)} messages</div>
  </div>
  <div class="messages">
{content.replace("**User:**", '<div class="message user"><div class="role">User</div>').replace("**Assistant:**", '<div class="message assistant"><div class="role">Assistant</div>').replace("\n", "<br>") if content else ""}
  </div>
</body>
</html>"""
                return html_content


_store: Optional[ConversationStore] = None


def get_store() -> ConversationStore:
    global _store
    if _store is None:
        _store = ConversationStore()
    return _store
