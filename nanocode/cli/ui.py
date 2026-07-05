"""Terminal UI helpers — colors, box-drawing, spinner, text rendering."""

from __future__ import annotations

import re
import shutil
import sys
import threading
import time

from nanocode.cli.config import AGENT_FILES
from nanocode.cli.types import ToolResult, Ok, Err

__all__ = [
    "RESET", "BOLD", "DIM", "BLACK", "RED", "GREEN", "YELLOW",
    "BLUE", "MAGENTA", "CYAN", "WHITE", "GRAY",
    "BG_RED", "BG_GREEN", "BG_BLUE",

    "separator", "_hdr", "_ftr", "_mid", "_BOX", "_tw",
    "_spinner_start", "_spinner_stop",
    "_render_text_block", "render_markdown",
    "print_help", "print_skills", "print_tool_call", "print_tool_result",
    "_recap_line", "endpoint_kind",
]

# --- ANSI colors ---

RESET, BOLD, DIM = "\033[0m", "\033[1m", "\033[2m"
BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = (
    "\033[30m", "\033[31m", "\033[32m", "\033[33m",
    "\033[34m", "\033[35m", "\033[36m", "\033[37m",
)
GRAY = "\033[90m"
BG_RED, BG_GREEN, BG_BLUE = "\033[41m", "\033[42m", "\033[44m"

# Force UTF-8 so box-drawing chars work on Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Detect if terminal supports Unicode box-drawing; fall back to ASCII
_HAS_UNICODE = sys.stdout.encoding and sys.stdout.encoding.lower().startswith("utf")
_BOX: dict[str, str] = {
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


def _tw() -> int:
    return shutil.get_terminal_size((80, 20)).columns


def _hdr(title: str, color: str | None = None) -> str:
    w = min(_tw(), 80)
    c = color or ""
    inner = f"\u2500 {title} "
    return f"{DIM}{_BOX['tl']}{c}{inner}{DIM}{_BOX['h'] * max(1, w - len(inner) - 2)}{_BOX['tr']}{RESET}"


def _ftr() -> str:
    w = min(_tw(), 80)
    return f"{DIM}{_BOX['bl']}{_BOX['h'] * max(1, w - 2)}{_BOX['br']}{RESET}"


def _mid() -> str:
    w = min(_tw(), 80)
    return f"{DIM}{_BOX['ml']}{_BOX['h'] * max(1, w - 2)}{_BOX['ml']}{RESET}"


def separator() -> str:
    w = min(_tw(), 80)
    return f"{DIM}{'\u2500' * w}{RESET}"


# --- spinner ---

_spin = False
_SPINNER = "\u280b\u2819\u2839\u2838\u283c\u2834\u2826\u2827\u2807\u280f"


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


def _render_text_block(text: str) -> str:
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


def render_markdown(text: str) -> str:
    text = re.sub(r"\*\*(.+?)\*\*", f"{BOLD}\\1{RESET}", text)
    text = re.sub(r"`([^`]+)`", f"{YELLOW}\\1{RESET}", text)
    return text


def print_help(current_model: str, current_mode: str, current_skill: str | None) -> None:
    cmds = [
        ("/q, exit", "quit"),
        ("/c", "clear conversation"),
        ("/models", "fetch and list models"),
        ("/model", "show current model"),
        ("/model <n>", "switch model; clears conv"),
        ("/plan", "switch to plan mode (read-only tools)"),
        ("/build", "switch to build mode (full access)"),
        ("/skills", "list available skills"),
        ("/use <name>", "load a skill prompt"),
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
    mode_color = GREEN if current_mode == "build" else YELLOW
    skill_tag = f" \u00b7 {current_skill}" if current_skill else ""
    print(
        f"\n{GRAY}model{RESET}  {current_model} ({endpoint_kind(current_model)})"
        f"  {GRAY}mode{RESET}  {mode_color}{current_mode}{RESET}{skill_tag}"
    )


def print_skills(skills_list: list[str], current_skill: str | None, mode: str) -> None:
    from nanocode.cli.config import SKILL_CATALOG

    for i, skill_name in enumerate(skills_list, 1):
        marker = "*" if skill_name == current_skill else " "
        desc = SKILL_CATALOG.get(skill_name, "")
        desc_fragment = f" {GRAY}\u2014 {desc[:70]}{'...' if len(desc) > 70 else ''}{RESET}" if desc else ""
        if marker == "*":
            line = f"{marker} {i:2}. {BOLD}{skill_name}{RESET}{desc_fragment} {GREEN}(active){RESET}"
        else:
            line = f"{marker} {i:2}. {skill_name}{desc_fragment}"
        print(f"  {line}")


def print_tool_call(tool_name: str, tool_args: dict) -> None:
    values = list(tool_args.values()) if isinstance(tool_args, dict) else []
    arg_preview = str(values[0])[:70] if values else ""
    print(f"\n{_hdr(tool_name, GREEN)}")
    if arg_preview:
        print(f"{DIM}{_BOX['v']}{RESET} {GRAY}{arg_preview}{RESET}")
        print(_ftr())


def print_tool_result(tool_name: str, tool_args: dict, result: ToolResult) -> None:
    if isinstance(result, Err):
        print(f"  {RED}\u2717 {result.message}{RESET}")
        return

    msg = result.message

    if tool_name == "edit" and msg == "ok":
        old = tool_args.get("old", "")
        new = tool_args.get("new", "")
        old_line = old.split("\n")[0]
        new_line = new.split("\n")[0]
        if len(old_line) > 60:
            old_line = old_line[:57] + "..."
        if len(new_line) > 60:
            new_line = new_line[:57] + "..."
        print(f"  {RED}\u2212 {GRAY}{old_line}{RESET}")
        print(f"  {GREEN}+ {GRAY}{new_line}{RESET}")
        return

    msg_lines = msg.split("\n")
    preview = msg_lines[0][:60] if msg_lines else "(empty)"
    if len(msg_lines) > 1:
        preview += f" {DIM}\u2026 +{len(msg_lines) - 1}{RESET}"
    elif msg_lines and len(msg_lines[0]) > 60:
        preview = preview[:57] + f"{DIM}\u2026{RESET}"
    print(f"  {DIM}{_BOX['bl']} {preview}{RESET}")


def _recap_line(model: str, mode: str, skill: str | None, msg_count: int, elapsed: float) -> None:
    mode_color = GREEN if mode == "build" else YELLOW
    skill_label = skill if skill else "no-skill"
    print(
        f"\n{GRAY}{model} \u00b7 {mode_color}{mode}{GRAY} \u00b7 {skill_label}"
        f" \u00b7 {msg_count} msgs \u00b7 {elapsed:.1f}s{RESET}"
    )


def endpoint_kind(model: str) -> str:
    from nanocode.cli.config import ANTHROPIC_COMPAT_MODELS as ACM

    model = model.removeprefix("opencode-go/").strip()
    if model in ACM or model.startswith("minimax-") or model.startswith("qwen"):
        return "anthropic"
    return "openai"
