"""Terminal UI helpers — colors, box-drawing, spinner, text rendering."""

import re
import shutil
import sys
import threading
import time

from nanocode.cli.config import AGENT_FILES

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
    "coder": "\u25c6",
    "architect": "\u25c7",
    "reviewer": "\u25cb",
    "debugger": "\u25b3",
    "tester": "\u25b7",
    "refactor": "\u21bb",
}

# Force UTF-8 so box-drawing chars work on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

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


def separator():
    w = min(_tw(), 80)
    return f"{DIM}{'─' * w}{RESET}"


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
    time.sleep(0.05)


# --- text rendering ---


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


def print_agents(current_agent):
    for i, agent_id in enumerate(list(AGENT_FILES.keys()), 1):
        marker = "*" if agent_id == current_agent else " "
        color = AGENT_COLORS.get(agent_id, "")
        icon = AGENT_ICONS.get(agent_id, " ")
        line = f"{marker} {i:2}. {color}{icon} {agent_id}{RESET}"
        kind = AGENT_FILES.get(agent_id, "")
        print(f"  {line}")


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


def endpoint_kind(model):
    from nanocode.cli.config import ANTHROPIC_COMPAT_MODELS as ACM

    model = model.removeprefix("opencode-go/").strip()
    if model in ACM or model.startswith("minimax-") or model.startswith("qwen"):
        return "anthropic"
    return "openai"
