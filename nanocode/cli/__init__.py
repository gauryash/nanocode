#!/usr/bin/env python3
"""nanocode-go - minimal coding agent using OpenCode Go."""

from __future__ import annotations

import os
from pathlib import Path

from nanocode.cli.config import (
    MODEL, AGENT_FILES, AGENT_TOOLS, SKILLS_DIR,
    SKILL_CATALOG, _fs,
)
from nanocode.cli.tools import init_permission_manager, TOOLS
from nanocode.cli.types import Ok, Err
from nanocode.cli.ui import (
    BOLD, DIM, GRAY, GREEN, YELLOW, RED, BLUE, CYAN, WHITE, BG_RED, RESET,
    _hdr, _ftr, _BOX,
    _tw, separator, _recap_line,
    _render_text_block, print_help, print_skills,
    endpoint_kind,
)
from nanocode.cli.api import (
    fetch_models, run_openai_turn, run_anthropic_turn,
    classify_skill,
)
from nanocode.cli.session import (
    SessionPayload, SessionHeader,
    _new_session_id, save_session, load_session, list_sessions,
    _resolve_session_id,
)

__all__ = [
    "load_system_prompt",
    "main",
]

_PLAN_TOOLS = {"read", "glob", "grep"}

# Throttle state for skill auto-classification
_last_classified_msg: str = ""
_last_skill_classification: str | None = None


def load_system_prompt() -> str:
    """Load the base system prompt (``nanocode/system.md`` or override)."""
    from nanocode.cli.config import SYSTEM_PROMPT_PATH
    try:
        return _fs.read_text(Path(SYSTEM_PROMPT_PATH)).strip()
    except FileNotFoundError:
        return ""


def load_skill_prompt(skill_name: str) -> str:
    """Load a skill prompt file from ``SKILLS_DIR``."""
    fn = AGENT_FILES.get(skill_name, "")
    if not fn:
        raise ValueError(f"unknown skill {skill_name!r}")
    path = Path(SKILLS_DIR) / fn
    template = _fs.read_text(path)
    return template.format(cwd=os.getcwd())


def build_system_prompt(skill_name: str | None) -> str:
    """Combine base system prompt with skill prompt (if any)."""
    base = load_system_prompt()
    if skill_name and skill_name in AGENT_FILES:
        skill_prompt = load_skill_prompt(skill_name)
        return base + "\n\n" + skill_prompt
    return base


def _effective_tools(mode: str, skill: str | None) -> set[str]:
    """Resolve the tool set for a mode + skill combination."""
    if mode == "plan":
        return _PLAN_TOOLS
    if skill and skill in AGENT_TOOLS:
        return AGENT_TOOLS[skill]
    return set(TOOLS.keys())


def list_skills() -> list[str]:
    """Return all skill names sorted."""
    return sorted(AGENT_FILES.keys())


def _classify_and_maybe_switch(
    user_message: str,
    current_model: str,
    current_skill: str | None,
) -> str | None:
    """Check if the user's message suggests a different skill and switch if confident.

    Returns the new skill name if switched, None if unchanged.
    """
    global _last_classified_msg, _last_skill_classification

    if not SKILL_CATALOG:
        return None

    # Throttle: skip very short messages and repeated classifications
    msg_stripped = user_message.strip()
    if len(msg_stripped) < 10 or msg_stripped == _last_classified_msg:
        return None

    skill_name, confidence = classify_skill(msg_stripped, SKILL_CATALOG, current_model)
    _last_classified_msg = msg_stripped

    if not skill_name or confidence < 0.4:
        _last_skill_classification = None
        return None

    if confidence < 0.7:
        # Low confidence — show a dim hint, don't switch
        _last_skill_classification = None
        print(f"  {DIM}· hint:{RESET} {BOLD}{skill_name}{RESET} {DIM}({confidence:.0%} match · /use {skill_name} to activate){RESET}")
        return None

    if skill_name == current_skill:
        _last_skill_classification = skill_name
        return None

    if skill_name in AGENT_FILES:
        _last_skill_classification = skill_name
        if confidence >= 0.8:
            print(f"  {GREEN}=> Auto-switched to skill{RESET} {BOLD}{skill_name}{RESET} {GRAY}({confidence:.0%} match){RESET}")
            return skill_name
        print(f"  {YELLOW}=> Suggested skill{RESET} {BOLD}{skill_name}{RESET} {GRAY}({confidence:.0%} match) — use /use {skill_name} to switch{RESET}")
        return None

    return None


def choose_skill(arg: str) -> str:
    """Resolve a skill name or number to a validated skill ID."""
    ids = list_skills()
    if arg.isdigit():
        idx = int(arg) - 1
        if 0 <= idx < len(ids):
            return ids[idx]
        raise ValueError(f"skill number must be between 1 and {len(ids)}")
    if arg not in AGENT_FILES:
        raise ValueError(f"unknown skill {arg!r}; use /skills to list")
    return arg


def choose_model(arg: str, model_cache: list[str]) -> str:
    """Resolve a model name or number to a validated model ID."""
    from nanocode.cli.config import ANTHROPIC_COMPAT_MODELS

    arg = arg.removeprefix("opencode-go/").strip()
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
        print(f"{YELLOW}\u26a0  Warning: {arg!r} was not in /models; trying anyway.{RESET}")
    return arg


def main() -> None:
    current_model = MODEL.removeprefix("opencode-go/").strip()
    model_cache: list[str] = []
    current_mode = "build"
    current_skill: str | None = None
    messages: list[dict] = []
    session_id = _new_session_id()

    init_permission_manager()

    mode_color = GREEN if current_mode == "build" else YELLOW
    skill_tag = f" \u00b7 {current_skill}" if current_skill else f" \u00b7 {DIM}no-skill{RESET}"
    header = (
        f"{BOLD}nanocode-go{RESET} {GRAY}\u00b7{RESET} "
        f"{DIM}{current_model} ({endpoint_kind(current_model)}){RESET} "
        f"{GRAY}\u00b7{RESET} "
        f"{mode_color}{current_mode}{RESET}{skill_tag} "
        f"{GRAY}\u00b7{RESET} "
        f"{DIM}{os.getcwd()}{RESET}"
    )
    w = min(_tw(), 80)
    print(f"{DIM}{_BOX['tl']}{_BOX['h'] * max(1, w - 2)}{_BOX['tr']}{RESET}")
    print(f"{DIM}{_BOX['v']}{RESET} {header}")
    print(f"{DIM}{_BOX['bl']}{_BOX['h'] * max(1, w - 2)}{_BOX['br']}{RESET}")
    n_skills = len(AGENT_FILES)
    print(f"{DIM}  session {session_id}{RESET}  {GRAY}{n_skills} skills available · /skills to list{RESET}\n")

    while True:
        try:
            print(separator())
            user_input = input(f"{BOLD}{BLUE}>{RESET} ").strip()
            print(separator())
            if not user_input:
                continue

            if user_input in ("/q", "exit"):
                save_session(SessionPayload(
                    session_id=session_id,
                    model=current_model,
                    mode=current_mode,
                    skill=current_skill,
                    messages=messages,
                ))
                break

            if user_input == "/help":
                print_help(current_model, current_mode, current_skill)
                continue

            if user_input == "/c":
                messages = []
                save_session(SessionPayload(
                    session_id=session_id,
                    model=current_model,
                    mode=current_mode,
                    skill=current_skill,
                    messages=messages,
                ))
                print(f"  {GREEN}\u2713 Cleared conversation{RESET}")
                continue

            if user_input == "/models":
                model_cache = fetch_models()
                print(_hdr("Models"))
                for i, mid in enumerate(model_cache, 1):
                    marker = "*" if mid == current_model else " "
                    kind = endpoint_kind(mid)
                    print(f"{DIM}{_BOX['v']}{RESET} {marker} {i:2}. {BOLD if marker == '*' else ''}{mid}{RESET} {GRAY}({kind}){RESET}")
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
                    messages = []
                    print(
                        f"  {GREEN}\u2713 Switched to {BOLD}{current_model}{RESET}"
                        f" {GRAY}({endpoint_kind(current_model)}) \u2014 conversation cleared{RESET}"
                    )
                else:
                    print(f"  {GRAY}Already using {current_model}{RESET}")
                continue

            if user_input == "/sessions":
                sessions = list_sessions()
                print(_hdr(f"Sessions ({len(sessions)})"))
                for s in sessions:
                    marker = "*" if s.session_id == session_id else " "
                    skill_tag = f" \u00b7 {s.skill}" if s.skill else ""
                    print(
                        f"{DIM}{_BOX['v']}{RESET} {marker} {BOLD if marker == '*' else ''}{s.session_id}{RESET}"
                        f"  {GRAY}{s.model} \u00b7 {s.mode}{skill_tag}"
                        f" \u00b7 {s.message_count} msgs"
                        f" \u00b7 {s.updated}{RESET}"
                    )
                print(_ftr())
                continue

            if user_input == "/session":
                skill_label = current_skill if current_skill else f"{DIM}(none){RESET}"
                print(f"  {GRAY}Session{RESET}  {BOLD}{session_id}{RESET}")
                print(f"  {GRAY}Messages{RESET} {len(messages)}  {GRAY}Model{RESET} {current_model}  {GRAY}Mode{RESET} {current_mode}  {GRAY}Skill{RESET} {skill_label}")
                continue

            if user_input == "/session new":
                save_session(SessionPayload(
                    session_id=session_id,
                    model=current_model,
                    mode=current_mode,
                    skill=current_skill,
                    messages=messages,
                ))
                session_id = _new_session_id()
                messages = []
                print(f"  {GREEN}\u2713 New session{RESET}  {BOLD}{session_id}{RESET}")
                continue

            if user_input.startswith("/session "):
                _, raw_sid = user_input.split(maxsplit=1)
                try:
                    target_id = _resolve_session_id(raw_sid)
                    save_session(SessionPayload(
                        session_id=session_id,
                        model=current_model,
                        mode=current_mode,
                        skill=current_skill,
                        messages=messages,
                    ))
                    data = load_session(target_id)
                    messages = data.messages
                    session_id = target_id
                    if data.model:
                        current_model = data.model
                    if data.mode:
                        current_mode = data.mode
                    current_skill = data.skill
                    mode_color = GREEN if current_mode == "build" else YELLOW
                    skill_tag = f" \u00b7 {current_skill}" if current_skill else ""
                    print(f"  {GREEN}\u2713 Restored{RESET} {BOLD}{session_id}{RESET}"
                          f" {GRAY}{current_model} \u00b7 {mode_color}{current_mode}{GRAY}{skill_tag}{RESET}")
                except ValueError as e:
                    print(f"  {RED}\u2717 {e}{RESET}")
                except Exception as e:
                    print(f"  {RED}\u2717 failed to load session: {e}{RESET}")
                continue

            if user_input == "/plan":
                if current_mode != "plan":
                    current_mode = "plan"
                    skill_label = current_skill if current_skill else f"{DIM}no-skill{RESET}"
                    print(f"  {YELLOW}\u25b6  Plan mode{RESET}  {GRAY}· {skill_label} · read-only tools (read, glob, grep){RESET}")
                else:
                    print(f"  {GRAY}Already in plan mode{RESET}")
                continue

            if user_input == "/build":
                if current_mode != "build":
                    current_mode = "build"
                    skill_label = current_skill if current_skill else f"{DIM}no-skill{RESET}"
                    print(f"  {GREEN}\u25b6  Build mode{RESET}  {GRAY}· {skill_label}{RESET}")
                else:
                    print(f"  {GRAY}Already in build mode{RESET}")
                continue

            if user_input == "/skills":
                ids = list_skills()
                print(_hdr("Skills"))
                print_skills(ids, current_skill, current_mode)
                print(_ftr())
                continue

            if user_input.startswith("/use "):
                _, raw_skill = user_input.split(maxsplit=1)
                try:
                    new_skill = choose_skill(raw_skill)
                    if new_skill != current_skill:
                        current_skill = new_skill
                        print(f"  {GREEN}\u2713 Loaded skill{RESET}  {BOLD}{current_skill}{RESET}")
                    else:
                        print(f"  {GRAY}Already using {current_skill}{RESET}")
                except ValueError as e:
                    print(f"  {RED}\u2717 {e}{RESET}")
                continue

            # Auto-classify skill from the user message (works in plan + build)
            switched = _classify_and_maybe_switch(user_input, current_model, current_skill)
            if switched:
                current_skill = switched
                mode_color = GREEN if current_mode == "build" else YELLOW

            messages.append({"role": "user", "content": user_input})
            system_prompt = build_system_prompt(current_skill)
            allowed_tools = _effective_tools(current_mode, current_skill)

            total_elapsed = 0.0
            while True:
                kind = endpoint_kind(current_model)
                if kind == "anthropic":
                    has_more_tools, elapsed = run_anthropic_turn(
                        messages, system_prompt, current_model, allowed_tools,
                    )
                else:
                    has_more_tools, elapsed = run_openai_turn(
                        messages, system_prompt, current_model, allowed_tools,
                    )
                total_elapsed += elapsed
                if not has_more_tools:
                    break

            _recap_line(current_model, current_mode, current_skill, len(messages), total_elapsed)
            save_session(SessionPayload(
                session_id=session_id,
                model=current_model,
                mode=current_mode,
                skill=current_skill,
                messages=messages,
            ))
            print()

        except (KeyboardInterrupt, EOFError):
            print()
            break
        except Exception as err:
            print(f"\n  {BG_RED}{WHITE} Error {RESET} {RED}{err}{RESET}")


if __name__ == "__main__":
    main()
