"""Session persistence — save/load conversation sessions."""

import json
import secrets
import sys
from datetime import datetime, timezone
from pathlib import Path

from nanocode.cli.config import _fs, SESSIONS_DIR, AGENT_FILES
from nanocode.cli.ui import YELLOW, RESET


def _ensure_sessions_dir():
    _fs.ensure_dir(Path(SESSIONS_DIR))


def _new_session_id():
    return secrets.token_hex(5)  # 10 hex chars


def save_session(session_id, conversations, model, agent):
    _ensure_sessions_dir()
    path = Path(SESSIONS_DIR) / f"{session_id}.json"
    payload = {
        "id": session_id,
        "model": model,
        "agent": agent,
        "conversations": conversations,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    content = json.dumps(payload, indent=2, ensure_ascii=False)
    _fs.write_text(path, content)


def load_session(session_id):
    path = Path(SESSIONS_DIR) / f"{session_id}.json"
    try:
        content = _fs.read_text(path)
        data = json.loads(content)
    except (json.JSONDecodeError, OSError) as e:
        raise RuntimeError(f"failed to load session '{session_id}': {e}") from e
    return data["conversations"], data.get("model"), data.get("agent")


def list_sessions():
    _ensure_sessions_dir()
    sessions = []
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
            sessions.append({
                "id": sid,
                "model": data.get("model", "?"),
                "agent": data.get("agent", "?"),
                "messages": total_msgs,
                "updated": data.get("updated_at", "")[:19],
            })
        except Exception:
            sessions.append({"id": entry.stem, "model": "?", "agent": "?", "messages": 0, "updated": ""})
            print(f"{YELLOW}Warning: corrupt session file '{entry.name}' skipped.{RESET}", file=sys.stderr)
    sessions.sort(key=lambda s: s["updated"], reverse=True)
    return sessions


def _resolve_session_id(prefix):
    """Match a session by ID prefix. Returns full id or raises ValueError."""
    sessions = list_sessions()
    matches = [s["id"] for s in sessions if s["id"].startswith(prefix)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) == 0:
        raise ValueError(f"no session matches prefix '{prefix}'")
    raise ValueError(f"prefix '{prefix}' matches {len(matches)} sessions; be more specific")
