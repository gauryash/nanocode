#!/usr/bin/env python3
"""nanocode-go - minimal coding agent using OpenCode Go.

Environment:
  export OPENCODE_GO_API_KEY="..."
  export MODEL="deepseek-v4-flash"   # optional, default shown

Commands inside the REPL:
  /q, exit          quit
  /c                clear conversation
  /models           fetch and list OpenCode Go models
  /model            show current model
  /model <id|num>   switch model; clears conversation
  /agents           list available agents
  /agent            show current agent
  /agent <id|num>   switch agent
  /askall <prompt>  send prompt to all agents
  /sessions         list saved sessions
  /session          show current session
  /session new      save & start new session
  /session <id>     restore session by ID prefix
  /help             show commands
"""

import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

from pathlib import Path

from nanocode.permission import PermissionManager
from nanocode.permission.fs_wrapper import FileSystemWrapper

# Framework-global FileSystemWrapper (trusted — used for NanoCode's own files)
_fs: FileSystemWrapper = FileSystemWrapper()

# --- inline .env loader (zero deps) ---


def _load_dotenv(path=".env"):
    """Load KEY=VALUE pairs from a .env file.  Does NOT override existing env vars.

    This is a framework operation (not an agent action).
    """
    try:
        env_path = Path(path).resolve()
        content = _fs.read_text(env_path)
        for line in content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip()
            if key and key not in os.environ:
                os.environ[key] = value
    except FileNotFoundError:
        pass
    except OSError:
        pass


_load_dotenv()  # load .env from CWD before reading env vars

OPENCODE_GO_KEY = os.environ.get("OPENCODE_GO_API_KEY") or os.environ.get("OPENCODE_API_KEY")
MODELS_URL = "https://opencode.ai/zen/go/v1/models"
CHAT_COMPLETIONS_URL = "https://opencode.ai/zen/go/v1/chat/completions"
MESSAGES_URL = "https://opencode.ai/zen/go/v1/messages"
DEFAULT_MODEL = "deepseek-v4-flash"
MODEL = os.environ.get("MODEL", DEFAULT_MODEL)
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "8192"))

DEFAULT_AGENT = os.environ.get("AGENT", "coder")
AGENTS_DIR = os.environ.get("AGENTS_DIR", "agents")
SESSIONS_DIR = os.path.join(os.getcwd(), ".nanocode", "sessions")

AGENT_FILES = {
    "coder": "coder.md",
    "architect": "architect.md",
    "reviewer": "reviewer.md",
    "debugger": "debugger.md",
    "tester": "tester.md",
    "refactor": "refactor.md",
}

# Per-agent tool allowlists (code-level enforcement).
# Only coder gets write/edit; all others are read-only.
AGENT_TOOLS = {
    "coder":     {"read", "write", "edit", "glob", "grep", "bash"},
    "architect": {"read", "glob", "grep"},
    "reviewer":  {"read", "glob", "grep"},
    "debugger":  {"read", "glob", "grep", "bash"},
    "tester":    {"read", "glob", "grep"},
    "refactor":  {"read", "glob", "grep"},
}

# OpenCode Go docs currently mark these families as Anthropic-compatible /messages.
ANTHROPIC_COMPAT_MODELS = {
    "minimax-m3",
    "minimax-m2.7",
    "minimax-m2.5",
    "qwen3.7-max",
    "qwen3.7-plus",
    "qwen3.6-plus",
    "qwen3.5-plus",
}

# --- ANSI colors ---

RESET, BOLD, DIM = "\033[0m", "\033[1m", "\033[2m"
BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = (
    "\033[30m", "\033[31m", "\033[32m", "\033[33m",
    "\033[34m", "\033[35m", "\033[36m", "\033[37m",
)
GRAY = "\033[90m"
BG_RED, BG_GREEN, BG_BLUE = "\033[41m", "\033[42m", "\033[44m"

AGENT_COLORS = {
    "coder": BLUE,
    "architect": MAGENTA,
    "reviewer": YELLOW,
    "debugger": RED,
    "tester": GREEN,
    "refactor": CYAN,
}

AGENT_ICONS = {
    "coder": "◆",
    "architect": "◇",
    "reviewer": "○",
    "debugger": "△",
    "tester": "▷",
    "refactor": "↻",
}

# Force UTF-8 so box-drawing chars work on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# --- box-drawing helpers ---

# Detect if terminal supports Unicode box-drawing; fall back to ASCII
_HAS_UNICODE = sys.stdout.encoding and sys.stdout.encoding.lower().startswith("utf")
_BOX = {
    "tl": "╭" if _HAS_UNICODE else ".",
    "tr": "╮" if _HAS_UNICODE else ".",
    "bl": "╰" if _HAS_UNICODE else "'",
    "br": "╯" if _HAS_UNICODE else "'",
    "ml": "├" if _HAS_UNICODE else "|",
    "v": "│" if _HAS_UNICODE else "|",
    "h": "─" if _HAS_UNICODE else "-",
    # code-block borders (lighter weight)
    "ctl": "┌" if _HAS_UNICODE else ",",
    "ctr": "┐" if _HAS_UNICODE else ",",
    "cbl": "└" if _HAS_UNICODE else "'",
    "cbr": "┘" if _HAS_UNICODE else "'",
}


def _tw():
    return shutil.get_terminal_size((80, 20)).columns


def _hdr(title, color=None):
    """╭─ title ──────────────────────╮"""
    w = min(_tw(), 80)
    c = color or ""
    inner = f"─ {title} "
    return f"{DIM}{_BOX['tl']}{c}{inner}{DIM}{_BOX['h'] * max(1, w - len(inner) - 2)}{_BOX['tr']}{RESET}"


def _ftr():
    """╰──────────────────────────────╯"""
    w = min(_tw(), 80)
    return f"{DIM}{_BOX['bl']}{_BOX['h'] * max(1, w - 2)}{_BOX['br']}{RESET}"


def _mid():
    """├──────────────────────────────┤"""
    w = min(_tw(), 80)
    return f"{DIM}{_BOX['ml']}{_BOX['h'] * max(1, w - 2)}{_BOX['ml']}{RESET}"


# --- spinner ---

_spin = False
_SPINNER = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


def _spin_thread():
    i = 0
    while _spin:
        sys.stdout.write(f"\r{GRAY}{_SPINNER[i % len(_SPINNER)]} Thinking...{RESET}")
        sys.stdout.flush()
        time.sleep(0.08)
        i += 1
    sys.stdout.write("\r" + " " * 20 + "\r")
    sys.stdout.flush()


def _spinner_start():
    global _spin
    _spin = True
    t = threading.Thread(target=_spin_thread, daemon=True)
    t.start()
    return t


def _spinner_stop():
    global _spin
    _spin = False
    time.sleep(0.05)  # let thread clear the line


# Global PermissionManager instance (initialized at startup).
# Every filesystem operation must route through this.
_pm: PermissionManager | None = None


def init_permission_manager():
    """Initialize the global PermissionManager from the CWD."""
    global _pm
    _pm = PermissionManager(Path.cwd())
    return _pm


def get_permission_manager() -> PermissionManager:
    assert _pm is not None, "PermissionManager not initialized"
    return _pm


# --- Agent prompt system ---


def load_agent_prompt(agent_id):
    if agent_id not in AGENT_FILES:
        raise ValueError(f"unknown agent {agent_id!r}")

    path = Path(AGENTS_DIR) / AGENT_FILES[agent_id]

    # Agent prompts are framework operations inside the workspace
    template = _fs.read_text(path)

    return template.format(cwd=os.getcwd())


def list_agents():
    return list(AGENT_FILES.keys())


def agent_system_prompt(agent_id):
    return load_agent_prompt(agent_id)


def print_agents(current_agent):
    for i, agent_id in enumerate(list_agents(), 1):
        marker = "*" if agent_id == current_agent else " "
        color = AGENT_COLORS.get(agent_id, "")
        icon = AGENT_ICONS.get(agent_id, " ")
        line = f"{marker} {i:2}. {color}{icon} {agent_id}{RESET}"
        kind = AGENT_FILES.get(agent_id, "")
        print(f"  {line}")


def choose_agent(arg):
    agent_ids = list_agents()

    if arg.isdigit():
        idx = int(arg) - 1
        if 0 <= idx < len(agent_ids):
            return agent_ids[idx]
        raise ValueError(f"agent number must be between 1 and {len(agent_ids)}")

    if arg not in AGENT_FILES:
        raise ValueError(f"unknown agent {arg!r}; use /agents to list agents")

    return arg


# --- Tool implementations ---


def read(args):
    pm = get_permission_manager()
    path = args["path"]
    offset = int(args.get("offset", 0))
    limit = int(args["limit"]) if args.get("limit") is not None else None
    try:
        return pm.read_text(path, reason="Agent requested file read", offset=offset, limit=limit)
    except PermissionError as e:
        return f"error: {e}"


def write(args):
    pm = get_permission_manager()
    path = args["path"]
    content = args["content"]
    try:
        pm.write_text(path, content, reason="Agent requested file write")
        return "ok"
    except PermissionError as e:
        return f"error: {e}"


def edit(args):
    pm = get_permission_manager()
    path = args["path"]
    old = args["old"]
    new = args["new"]
    all_occurrences = args.get("all", False)
    try:
        return pm.edit_text(path, old, new, all_occurrences, reason="Agent requested file edit")
    except PermissionError as e:
        return f"error: {e}"


def glob(args):
    pm = get_permission_manager()
    pattern = args["pat"]
    root = args.get("path", ".")
    try:
        return pm.glob(pattern, root, reason="Agent requested file search")
    except PermissionError as e:
        return f"error: {e}"


def grep(args):
    pm = get_permission_manager()
    pattern = args["pat"]
    root = args.get("path", ".")
    try:
        return pm.grep(pattern, root, reason="Agent requested text search")
    except PermissionError as e:
        return f"error: {e}"


def bash(args):
    pm = get_permission_manager()
    command = args["cmd"]
    try:
        def stream(line):
            print(f"  {DIM}{_BOX['v']}{RESET} {line}", flush=True)
        result = pm.run_command(command, reason="Agent requested shell command", line_callback=stream)
        return result
    except PermissionError as e:
        return f"error: {e}"


# --- Tool definitions: (description, schema, function) ---

TOOLS = {
    "read": (
        "Read file with line numbers (file path, not directory)",
        {"path": "string", "offset": "number?", "limit": "number?"},
        read,
    ),
    "write": (
        "Write content to file",
        {"path": "string", "content": "string"},
        write,
    ),
    "edit": (
        "Replace old with new in file (old must be unique unless all=true)",
        {"path": "string", "old": "string", "new": "string", "all": "boolean?"},
        edit,
    ),
    "glob": (
        "Find files by pattern, sorted by mtime",
        {"pat": "string", "path": "string?"},
        glob,
    ),
    "grep": (
        "Search files for regex pattern",
        {"pat": "string", "path": "string?"},
        grep,
    ),
    "bash": (
        "Run shell command",
        {"cmd": "string"},
        bash,
    ),
}


def run_tool(name, args, agent_id=None):
    if agent_id and agent_id in AGENT_TOOLS and name not in AGENT_TOOLS[agent_id]:
        return f"error: tool '{name}' is not available for agent '{agent_id}'"
    try:
        return TOOLS[name][2](args)
    except Exception as err:
        return f"error: {err}"


def json_type(param_type):
    base_type = param_type.rstrip("?")
    if base_type == "number":
        return "integer"
    return base_type


def make_properties(params):
    properties = {}
    required = []
    for param_name, param_type in params.items():
        is_optional = param_type.endswith("?")
        properties[param_name] = {"type": json_type(param_type)}
        if not is_optional:
            required.append(param_name)
    return properties, required


def make_anthropic_schema(allowed_tools=None):
    result = []
    tools = TOOLS if allowed_tools is None else {k: v for k, v in TOOLS.items() if k in allowed_tools}
    for name, (description, params, _fn) in tools.items():
        properties, required = make_properties(params)
        result.append(
            {
                "name": name,
                "description": description,
                "input_schema": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            }
        )
    return result


def make_openai_schema(allowed_tools=None):
    result = []
    tools = TOOLS if allowed_tools is None else {k: v for k, v in TOOLS.items() if k in allowed_tools}
    for name, (description, params, _fn) in tools.items():
        properties, required = make_properties(params)
        result.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": description,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                },
            }
        )
    return result


def strip_opencode_prefix(model):
    return model.removeprefix("opencode-go/").strip()


def endpoint_kind(model):
    model = strip_opencode_prefix(model)
    if model in ANTHROPIC_COMPAT_MODELS or model.startswith("minimax-") or model.startswith("qwen"):
        return "anthropic"
    return "openai"


def auth_headers(require_key=True, extra=None):
    if require_key and not OPENCODE_GO_KEY:
        raise RuntimeError("Set OPENCODE_GO_API_KEY before making model requests.")
    headers = {"Content-Type": "application/json", "User-Agent": "nanocode-go/1.0"}
    if OPENCODE_GO_KEY:
        headers["Authorization"] = f"Bearer {OPENCODE_GO_KEY}"
    if extra:
        headers.update(extra)
    return headers


def http_json(url, payload=None, headers=None):
    _spinner_start()
    try:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url, data=data, headers=headers or {})
        try:
            with urllib.request.urlopen(request) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            body = err.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {err.code}: {body}") from err
    finally:
        _spinner_stop()


def fetch_models():
    response = http_json(MODELS_URL, headers=auth_headers(require_key=False))
    return [item["id"] for item in response.get("data", [])]


def call_openai_api(messages, system_prompt, model, allowed_tools=None):
    payload = {
        "model": strip_opencode_prefix(model),
        "max_tokens": MAX_TOKENS,
        "messages": [{"role": "system", "content": system_prompt}] + messages,
        "tools": make_openai_schema(allowed_tools),
        "tool_choice": "auto",
    }
    return http_json(CHAT_COMPLETIONS_URL, payload, auth_headers(require_key=True))


def call_anthropic_api(messages, system_prompt, model, allowed_tools=None):
    payload = {
        "model": strip_opencode_prefix(model),
        "max_tokens": MAX_TOKENS,
        "system": system_prompt,
        "messages": messages,
        "tools": make_anthropic_schema(allowed_tools),
    }
    headers = auth_headers(require_key=True, extra={"anthropic-version": "2023-06-01"})
    return http_json(MESSAGES_URL, payload, headers)


def separator():
    w = min(_tw(), 80)
    return f"{DIM}{'─' * w}{RESET}"


def _render_text_block(text):
    """Render model response with code-block fences styled."""
    lines = text.split("\n")
    out = []
    in_code = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code = not in_code
            if in_code:
                lang = stripped[3:].strip()
                label = f" {lang} " if lang else " code "
                out.append(f"{DIM}{_BOX['ctl']}{label}{_BOX['h'] * max(1, 48 - len(label))}{_BOX['ctr']}{RESET}")
            else:
                out.append(f"{DIM}{_BOX['cbl']}{_BOX['h'] * 50}{_BOX['cbr']}{RESET}")
        elif in_code:
            out.append(f" {GRAY}{line}{RESET}")
        else:
            out.append(f"{CYAN}>{RESET} {render_markdown(line)}")
    return "\n".join(out)


def render_markdown(text):
    """Bold **text** and inline `code`."""
    text = re.sub(r"\*\*(.+?)\*\*", f"{BOLD}\\1{RESET}", text)
    text = re.sub(r"`([^`]+)`", f"{YELLOW}\\1{RESET}", text)
    return text


def print_help(current_model, current_agent):
    cmds = [
        ("/q, exit", "quit"),
        ("/c", "clear conversation"),
        ("/models", "fetch and list models"),
        ("/model", "show current model"),
        ("/model <n>", "switch model; clears conv"),
        ("/agents", "list available agents"),
        ("/agent", "show current agent"),
        ("/agent <n>", "switch agent"),
        ("/askall <p>", "send prompt to all agents"),
        ("/sessions", "list saved sessions"),
        ("/session", "show current session"),
        ("/session new", "start new session"),
        ("/session <id>", "restore session by prefix"),
        ("/help", "show this help"),
    ]
    cw = max(len(c) for c, _ in cmds)
    print(_hdr("Commands"))
    for cmd, desc in cmds:
        print(f"{DIM}{_BOX['v']}{RESET} {BOLD}{cmd:<{cw}}{RESET} {GRAY}{desc}{RESET}")
    print(_ftr())
    color = AGENT_COLORS.get(current_agent, "")
    print(
        f"\n{GRAY}model{RESET}  {current_model} ({endpoint_kind(current_model)})"
        f"  {GRAY}agent{RESET}  {color}{current_agent}{RESET}"
    )


def print_tool_call(tool_name, tool_args):
    values = list(tool_args.values()) if isinstance(tool_args, dict) else []
    arg_preview = str(values[0])[:70] if values else ""
    print(f"\n{_hdr(tool_name, GREEN)}")
    if arg_preview:
        print(f"{DIM}{_BOX['v']}{RESET} {GRAY}{arg_preview}{RESET}")
        print(_ftr())


def print_tool_result(tool_name, tool_args, result):
    """Print result — diff style for edits, inline for others."""
    if tool_name == "edit" and result == "ok":
        path = tool_args.get("path", "?")
        old = tool_args.get("old", "")
        new = tool_args.get("new", "")
        old_line = old.split("\n")[0]
        new_line = new.split("\n")[0]
        if len(old_line) > 60:
            old_line = old_line[:57] + "..."
        if len(new_line) > 60:
            new_line = new_line[:57] + "..."
        print(f"  {RED}− {GRAY}{old_line}{RESET}")
        print(f"  {GREEN}+ {GRAY}{new_line}{RESET}")
        return
    if result.startswith("error:"):
        print(f"  {RED}✗ {result[7:]}{RESET}")
        return
    result_lines = result.split("\n")
    preview = result_lines[0][:60] if result_lines else "(empty)"
    if len(result_lines) > 1:
        preview += f" {DIM}… +{len(result_lines) - 1}{RESET}"
    elif result_lines and len(result_lines[0]) > 60:
        preview = preview[:57] + f"{DIM}…{RESET}"
    print(f"  {DIM}{_BOX['bl']} {preview}{RESET}")


def _recap_line(model, agent, msg_count, elapsed):
    """Dim recap: model · agent · N messages · X.Xs"""
    color = AGENT_COLORS.get(agent, "")
    print(
        f"\n{GRAY}{model} · {color}{agent}{GRAY} · {msg_count} msgs"
        f" · {elapsed:.1f}s{RESET}"
    )


def parse_tool_args(raw):
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def run_openai_turn(messages, system_prompt, model, agent_id=None):
    allowed_tools = AGENT_TOOLS.get(agent_id) if agent_id else None
    t0 = time.time()
    response = call_openai_api(messages, system_prompt, model, allowed_tools)
    message = response.get("choices", [{}])[0].get("message", {})

    content = message.get("content") or ""
    if content:
        print(f"\n{_render_text_block(content)}")

    assistant_message = {"role": "assistant", "content": content}
    tool_calls = message.get("tool_calls") or []
    if tool_calls:
        assistant_message["tool_calls"] = tool_calls
    messages.append(assistant_message)

    if not tool_calls:
        return False, time.time() - t0

    for tool_call in tool_calls:
        function = tool_call.get("function", {})
        tool_name = function.get("name", "")
        tool_args = parse_tool_args(function.get("arguments"))
        print_tool_call(tool_name, tool_args)
        result = run_tool(tool_name, tool_args, agent_id)
        print_tool_result(tool_name, tool_args, result)
        messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call.get("id"),
                "name": tool_name,
                "content": result,
            }
        )
    return True, time.time() - t0


def run_anthropic_turn(messages, system_prompt, model, agent_id=None):
    allowed_tools = AGENT_TOOLS.get(agent_id) if agent_id else None
    t0 = time.time()
    response = call_anthropic_api(messages, system_prompt, model, allowed_tools)
    content_blocks = response.get("content", [])
    tool_results = []

    for block in content_blocks:
        if block.get("type") == "text":
            print(f"\n{_render_text_block(block.get('text', ''))}")

        if block.get("type") == "tool_use":
            tool_name = block.get("name", "")
            tool_args = block.get("input", {})
            print_tool_call(tool_name, tool_args)
            result = run_tool(tool_name, tool_args, agent_id)
            print_tool_result(tool_name, tool_args, result)
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.get("id"),
                    "content": result,
                }
            )

    messages.append({"role": "assistant", "content": content_blocks})

    if not tool_results:
        return False, time.time() - t0

    messages.append({"role": "user", "content": tool_results})
    return True, time.time() - t0


# --- session persistence ---


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
    content = _fs.read_text(path)
    data = json.loads(content)
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


def choose_model(arg, model_cache):
    arg = strip_opencode_prefix(arg)
    if not model_cache:
        try:
            model_cache[:] = fetch_models()
        except Exception:
            pass

    if arg.isdigit() and model_cache:
        idx = int(arg) - 1
        if 0 <= idx < len(model_cache):
            return model_cache[idx]
        raise ValueError(f"model number must be between 1 and {len(model_cache)}")

    if model_cache and arg not in model_cache:
        print(f"{YELLOW}⚠  Warning: {arg!r} was not in /models; trying anyway.{RESET}")
    return arg


def main():
    current_model = strip_opencode_prefix(MODEL)
    model_cache = []
    current_agent = DEFAULT_AGENT if DEFAULT_AGENT in AGENT_FILES else "coder"
    conversations = {agent_id: [] for agent_id in AGENT_FILES}
    session_id = _new_session_id()

    # Initialize the Permission Manager — this is the security boundary.
    # All subsequent filesystem operations must pass through this.
    init_permission_manager()

    # Bordered header
    agent_color = AGENT_COLORS.get(current_agent, "")
    header = (
        f"{BOLD}nanocode-go{RESET} {GRAY}·{RESET} "
        f"{DIM}{current_model} ({endpoint_kind(current_model)}){RESET} "
        f"{GRAY}·{RESET} "
        f"{agent_color}{current_agent}{RESET} {GRAY}·{RESET} "
        f"{DIM}{os.getcwd()}{RESET}"
    )
    w = min(_tw(), 80)
    # truncate if too wide
    print(f"{DIM}{_BOX['tl']}{_BOX['h'] * max(1, w - 2)}{_BOX['tr']}{RESET}")
    print(f"{DIM}{_BOX['v']}{RESET} {header}")
    print(f"{DIM}{_BOX['bl']}{_BOX['h'] * max(1, w - 2)}{_BOX['br']}{RESET}")
    print(f"{DIM}  session {session_id}{RESET}\n")

    while True:
        try:
            print(separator())
            user_input = input(f"{BOLD}{BLUE}>{RESET} ").strip()
            print(separator())
            if not user_input:
                continue

            if user_input in ("/q", "exit"):
                save_session(session_id, conversations, current_model, current_agent)
                break

            if user_input == "/help":
                print_help(current_model, current_agent)
                continue

            if user_input == "/c":
                conversations = {agent_id: [] for agent_id in AGENT_FILES}
                save_session(session_id, conversations, current_model, current_agent)
                print(f"  {GREEN}✓ Cleared all conversations{RESET}")
                continue

            if user_input == "/models":
                model_cache = fetch_models()
                print(_hdr("Models"))
                for i, model_id in enumerate(model_cache, 1):
                    marker = "*" if model_id == current_model else " "
                    kind = endpoint_kind(model_id)
                    print(f"{DIM}{_BOX['v']}{RESET} {marker} {i:2}. {BOLD if marker == '*' else ''}{model_id}{RESET} {GRAY}({kind}){RESET}")
                print(_ftr())
                continue

            if user_input == "/model":
                print(f"  {GRAY}Current model{RESET}  {BOLD}{current_model}{RESET} {GRAY}({endpoint_kind(current_model)}){RESET}")
                continue

            if user_input.startswith("/model ") or user_input.startswith("/m "):
                _, raw_model = user_input.split(maxsplit=1)
                new_model = choose_model(raw_model, model_cache)
                if new_model != current_model:
                    current_model = new_model
                    conversations = {agent_id: [] for agent_id in AGENT_FILES}
                    print(
                        f"  {GREEN}✓ Switched to {BOLD}{current_model}{RESET}"
                        f" {GRAY}({endpoint_kind(current_model)}) — conversations cleared{RESET}"
                    )
                else:
                    print(f"  {GRAY}Already using {current_model}{RESET}")
                continue

            if user_input == "/sessions":
                sessions = list_sessions()
                print(_hdr(f"Sessions ({len(sessions)})"))
                for s in sessions:
                    marker = "*" if s["id"] == session_id else " "
                    print(
                        f"{DIM}{_BOX['v']}{RESET} {marker} {BOLD if marker == '*' else ''}{s['id']}{RESET}"
                        f"  {GRAY}{s['model']} · {s['agent']} · {s['messages']} msgs"
                        f" · {s['updated']}{RESET}"
                    )
                print(_ftr())
                continue

            if user_input == "/session":
                print(f"  {GRAY}Session{RESET}  {BOLD}{session_id}{RESET}")
                total = sum(len(v) for v in conversations.values())
                print(f"  {GRAY}Messages{RESET} {total}  {GRAY}Model{RESET} {current_model}  {GRAY}Agent{RESET} {current_agent}")
                continue

            if user_input == "/session new":
                save_session(session_id, conversations, current_model, current_agent)
                session_id = _new_session_id()
                conversations = {agent_id: [] for agent_id in AGENT_FILES}
                print(f"  {GREEN}✓ New session{RESET}  {BOLD}{session_id}{RESET}")
                continue

            if user_input.startswith("/session "):
                _, raw_sid = user_input.split(maxsplit=1)
                try:
                    target_id = _resolve_session_id(raw_sid)
                    save_session(session_id, conversations, current_model, current_agent)
                    conversations, restored_model, restored_agent = load_session(target_id)
                    # Ensure all agent keys exist (backward compat)
                    for agent_id in AGENT_FILES:
                        conversations.setdefault(agent_id, [])
                    session_id = target_id
                    if restored_model:
                        current_model = restored_model
                    if restored_agent and restored_agent in AGENT_FILES:
                        current_agent = restored_agent
                    color = AGENT_COLORS.get(current_agent, "")
                    icon = AGENT_ICONS.get(current_agent, "")
                    print(f"  {GREEN}✓ Restored{RESET} {BOLD}{session_id}{RESET}"
                          f" {GRAY}{current_model} · {color}{icon} {current_agent}{RESET}")
                except ValueError as e:
                    print(f"  {RED}✗ {e}{RESET}")
                except Exception as e:
                    print(f"  {RED}✗ failed to load session: {e}{RESET}")
                continue

            if user_input == "/agents":
                print(_hdr("Agents"))
                print_agents(current_agent)
                print(_ftr())
                continue

            if user_input == "/agent":
                color = AGENT_COLORS.get(current_agent, "")
                icon = AGENT_ICONS.get(current_agent, "")
                print(f"  {color}{icon} {BOLD}{current_agent}{RESET}")
                continue

            if user_input.startswith("/agent "):
                _, raw_agent = user_input.split(maxsplit=1)
                new_agent = choose_agent(raw_agent)
                if new_agent != current_agent:
                    current_agent = new_agent
                    color = AGENT_COLORS.get(current_agent, "")
                    icon = AGENT_ICONS.get(current_agent, "")
                    print(f"  {GREEN}✓ Switched to{RESET} {color}{icon} {BOLD}{current_agent}{RESET}")
                else:
                    print(f"  {GRAY}Already using {current_agent}{RESET}")
                continue

            if user_input.startswith("/askall "):
                _, raw_prompt = user_input.split(maxsplit=1)
                print(_hdr(f"askall: {raw_prompt[:50]}{'…' if len(raw_prompt) > 50 else ''}"))
                for agent_id in AGENT_FILES:
                    color = AGENT_COLORS.get(agent_id, "")
                    icon = AGENT_ICONS.get(agent_id, "")
                    print(f"\n  {color}{icon} {BOLD}{agent_id}{RESET}")
                    messages = conversations.setdefault(agent_id, [])
                    messages.append({"role": "user", "content": raw_prompt})
                    system_prompt = agent_system_prompt(agent_id)

                    while True:
                        kind = endpoint_kind(current_model)
                        if kind == "anthropic":
                            has_more_tools, _ = run_anthropic_turn(messages, system_prompt, current_model, agent_id)
                        else:
                            has_more_tools, _ = run_openai_turn(messages, system_prompt, current_model, agent_id)
                        if not has_more_tools:
                            break
                print(f"\n{_ftr()}")
                continue

            messages = conversations[current_agent]
            messages.append({"role": "user", "content": user_input})
            system_prompt = agent_system_prompt(current_agent)

            total_elapsed = 0.0
            while True:
                kind = endpoint_kind(current_model)
                if kind == "anthropic":
                    has_more_tools, elapsed = run_anthropic_turn(messages, system_prompt, current_model, current_agent)
                else:
                    has_more_tools, elapsed = run_openai_turn(messages, system_prompt, current_model, current_agent)
                total_elapsed += elapsed
                if not has_more_tools:
                    break

            _recap_line(current_model, current_agent, len(messages), total_elapsed)
            save_session(session_id, conversations, current_model, current_agent)
            print()

        except (KeyboardInterrupt, EOFError):
            print()
            break
        except Exception as err:
            print(f"\n  {BG_RED}{WHITE} Error {RESET} {RED}{err}{RESET}")


if __name__ == "__main__":
    main()
