"""Session persistence — save/load conversation sessions."""

from __future__ import annotations

import json
import secrets
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from nanocode.cli.config import _fs, SESSIONS_DIR, AGENT_FILES
from nanocode.cli.ui import YELLOW, RESET

__all__ = [
    "SessionPayload", "SessionHeader",
    "save_session", "load_session", "list_sessions",
    "_new_session_id", "_resolve_session_id",
]


@dataclass
class SessionPayload:
    """Input to ``save_session`` — structured save data."""

    session_id: str
    model: str
    agent: str
    conversations: dict[str, list[dict]]


@dataclass
class SessionHeader:
    """Summary of a session for display in listings."""

    session_id: str
    model: str
    agent: str
    message_count: int
    updated: str


@dataclass
class SessionData:
    """Output from ``load_session`` — full session state."""

    conversations: dict[str, list[dict]]
    model: str | None
    agent: str | None


def _ensure_sessions_dir() -> None:
    _fs.ensure_dir(Path(SESSIONS_DIR))


def _new_session_id() -> str:
    return secrets.token_hex(5)


def save_session(session: SessionPayload) -> None:
    """Persist a conversation session to disk."""
    _ensure_sessions_dir()
    path = Path(SESSIONS_DIR) / f"{session.session_id}.json"
    now = datetime.now(timezone.utc).isoformat()
    payload = {
        "id": session.session_id,
        "model": session.model,
        "agent": session.agent,
        "conversations": session.conversations,
        "created_at": now,
        "updated_at": now,
    }
    content = json.dumps(payload, indent=2, ensure_ascii=False)
    _fs.write_text(path, content)


def load_session(session_id: str) -> SessionData:
    """Load a session by ID.

    Raises ``RuntimeError`` if the file is missing, corrupt, or unreadable.
    """
    path = Path(SESSIONS_DIR) / f"{session_id}.json"
    try:
        content = _fs.read_text(path)
        data = json.loads(content)
    except (json.JSONDecodeError, OSError) as e:
        raise RuntimeError(f"failed to load session '{session_id}': {e}") from e
    return SessionData(
        conversations=data["conversations"],
        model=data.get("model"),
        agent=data.get("agent"),
    )


def list_sessions() -> list[SessionHeader]:
    """List all saved sessions, newest first. Corrupt files are skipped with a warning."""
    _ensure_sessions_dir()
    sessions: list[SessionHeader] = []
    sessions_path = Path(SESSIONS_DIR)
    if not sessions_path.exists():
        return sessions
    for entry in sessions_path.iterdir():
        if not entry.name.endswith(".json"):
            continue
        try:
            content = _fs.read_text(entry)
            data = json.loads(content)
            sid = data.get("id", entry.stem)
            total_msgs = sum(len(v) for v in data.get("conversations", {}).values())
            sessions.append(SessionHeader(
                session_id=sid,
                model=data.get("model", "?"),
                agent=data.get("agent", "?"),
                message_count=total_msgs,
                updated=data.get("updated_at", "")[:19],
            ))
        except Exception:
            sessions.append(SessionHeader(
                session_id=entry.stem,
                model="?",
                agent="?",
                message_count=0,
                updated="",
            ))
            print(f"{YELLOW}Warning: corrupt session file '{entry.name}' skipped.{RESET}", file=sys.stderr)
    sessions.sort(key=lambda s: s.updated, reverse=True)
    return sessions


def _resolve_session_id(prefix: str) -> str:
    """Match a session by ID prefix. Returns full id or raises ``ValueError``."""
    sessions = list_sessions()
    matches = [s.session_id for s in sessions if s.session_id.startswith(prefix)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) == 0:
        raise ValueError(f"no session matches prefix '{prefix}'")
    raise ValueError(f"prefix '{prefix}' matches {len(matches)} sessions; be more specific")
