#!/usr/bin/env python3
"""nanocode-go - minimal coding agent using OpenCode Go.

Orchestration layer. Imports from submodules; no business logic here.
"""

from __future__ import annotations

import os
from pathlib import Path

from nanocode.cli.config import (
    MODEL, DEFAULT_AGENT, AGENT_FILES,
    _fs,
)
from nanocode.cli.tools import init_permission_manager, TOOLS
from nanocode.cli.types import Ok, Err
from nanocode.cli.ui import (
    BOLD, DIM, GRAY, GREEN, YELLOW, RED, BLUE, CYAN, WHITE, BG_RED, RESET,
    AGENT_COLORS, AGENT_ICONS,
    _hdr, _ftr, _BOX,
    _tw, separator, _recap_line,
    _render_text_block, print_help, print_agents,
    endpoint_kind,
)
from nanocode.cli.api import (
    fetch_models, run_openai_turn, run_anthropic_turn,
)
from nanocode.cli.session import (
    SessionPayload, SessionHeader,
    _new_session_id, save_session, load_session, list_sessions,
    _resolve_session_id,
)

__all__ = [
    "list_agents", "load_agent_prompt", "load_system_prompt",
    "agent_system_prompt", "choose_agent", "choose_model",
    "main",
]


# --- Agent prompt system ---


def load_agent_prompt(agent_id: str) -> str:
    """Load the agent-specific prompt file from ``AGENTS_DIR``."""
    if agent_id not in AGENT_FILES:
        raise ValueError(f"unknown agent {agent_id!r}")
    path = Path(os.environ.get("AGENTS_DIR", "agents")) / AGENT_FILES[agent_id]
    template = _fs.read_text(path)
    return template.format(cwd=os.getcwd())


def list_agents() -> list[str]:
    """Return all registered agent IDs."""
    return list(AGENT_FILES.keys())


def load_system_prompt() -> str:
    """Load the base system prompt (``nanocode/system.md`` or override)."""
    from nanocode.cli.config import SYSTEM_PROMPT_PATH
    try:
        return _fs.read_text(Path(SYSTEM_PROMPT_PATH)).strip()
    except FileNotFoundError:
        return ""


def agent_system_prompt(agent_id: str) -> str:
    """Combine system prompt + agent-specific prompt into one string."""
    agent_prompt = load_agent_prompt(agent_id)
    system_prompt = load_system_prompt()
    if system_prompt:
        return system_prompt + "\n\n" + agent_prompt
    return agent_prompt


def choose_agent(arg: str) -> str:
    """Resolve an agent name or number to a validated agent ID."""
    agent_ids = list_agents()
    if arg.isdigit():
        idx = int(arg) - 1
        if 0 <= idx < len(agent_ids):
            return agent_ids[idx]
        raise ValueError(f"agent number must be between 1 and {len(agent_ids)}")
    if arg not in AGENT_FILES:
        raise ValueError(f"unknown agent {arg!r}; use /agents to list agents")
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


# --- Main loop ---


def main() -> None:
    current_model = MODEL.removeprefix("opencode-go/").strip()
    model_cache: list[str] = []
    current_agent = DEFAULT_AGENT if DEFAULT_AGENT in AGENT_FILES else "coder"
    conversations: dict[str, list[dict]] = {agent_id: [] for agent_id in AGENT_FILES}
    session_id = _new_session_id()

    init_permission_manager()

    agent_color = AGENT_COLORS.get(current_agent, "")
    header = (
        f"{BOLD}nanocode-go{RESET} {GRAY}\u00b7{RESET} "
        f"{DIM}{current_model} ({endpoint_kind(current_model)}){RESET} "
        f"{GRAY}\u00b7{RESET} "
        f"{agent_color}{current_agent}{RESET} {GRAY}\u00b7{RESET} "
        f"{DIM}{os.getcwd()}{RESET}"
    )
    w = min(_tw(), 80)
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
                save_session(SessionPayload(
                    session_id=session_id,
                    model=current_model,
                    agent=current_agent,
                    conversations=conversations,
                ))
                break

            if user_input == "/help":
                print_help(current_model, current_agent)
                continue

            if user_input == "/c":
                conversations = {agent_id: [] for agent_id in AGENT_FILES}
                save_session(SessionPayload(
                    session_id=session_id,
                    model=current_model,
                    agent=current_agent,
                    conversations=conversations,
                ))
                print(f"  {GREEN}\u2713 Cleared all conversations{RESET}")
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
                    conversations = {agent_id: [] for agent_id in AGENT_FILES}
                    print(
                        f"  {GREEN}\u2713 Switched to {BOLD}{current_model}{RESET}"
                        f" {GRAY}({endpoint_kind(current_model)}) \u2014 conversations cleared{RESET}"
                    )
                else:
                    print(f"  {GRAY}Already using {current_model}{RESET}")
                continue

            if user_input == "/sessions":
                sessions = list_sessions()
                print(_hdr(f"Sessions ({len(sessions)})"))
                for s in sessions:
                    marker = "*" if s.session_id == session_id else " "
                    print(
                        f"{DIM}{_BOX['v']}{RESET} {marker} {BOLD if marker == '*' else ''}{s.session_id}{RESET}"
                        f"  {GRAY}{s.model} \u00b7 {s.agent} \u00b7 {s.message_count} msgs"
                        f" \u00b7 {s.updated}{RESET}"
                    )
                print(_ftr())
                continue

            if user_input == "/session":
                print(f"  {GRAY}Session{RESET}  {BOLD}{session_id}{RESET}")
                total = sum(len(v) for v in conversations.values())
                print(f"  {GRAY}Messages{RESET} {total}  {GRAY}Model{RESET} {current_model}  {GRAY}Agent{RESET} {current_agent}")
                continue

            if user_input == "/session new":
                save_session(SessionPayload(
                    session_id=session_id,
                    model=current_model,
                    agent=current_agent,
                    conversations=conversations,
                ))
                session_id = _new_session_id()
                conversations = {agent_id: [] for agent_id in AGENT_FILES}
                print(f"  {GREEN}\u2713 New session{RESET}  {BOLD}{session_id}{RESET}")
                continue

            if user_input.startswith("/session "):
                _, raw_sid = user_input.split(maxsplit=1)
                try:
                    target_id = _resolve_session_id(raw_sid)
                    save_session(SessionPayload(
                        session_id=session_id,
                        model=current_model,
                        agent=current_agent,
                        conversations=conversations,
                    ))
                    data = load_session(target_id)
                    conversations = data.conversations
                    for agent_id in AGENT_FILES:
                        conversations.setdefault(agent_id, [])
                    session_id = target_id
                    if data.model:
                        current_model = data.model
                    if data.agent and data.agent in AGENT_FILES:
                        current_agent = data.agent
                    color = AGENT_COLORS.get(current_agent, "")
                    icon = AGENT_ICONS.get(current_agent, "")
                    print(f"  {GREEN}\u2713 Restored{RESET} {BOLD}{session_id}{RESET}"
                          f" {GRAY}{current_model} \u00b7 {color}{icon} {current_agent}{RESET}")
                except ValueError as e:
                    print(f"  {RED}\u2717 {e}{RESET}")
                except Exception as e:
                    print(f"  {RED}\u2717 failed to load session: {e}{RESET}")
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
                    print(f"  {GREEN}\u2713 Switched to{RESET} {color}{icon} {BOLD}{current_agent}{RESET}")
                else:
                    print(f"  {GRAY}Already using {current_agent}{RESET}")
                continue

            if user_input.startswith("/askall "):
                _, raw_prompt = user_input.split(maxsplit=1)
                print(_hdr(f"askall: {raw_prompt[:50]}{'\u2026' if len(raw_prompt) > 50 else ''}"))
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
            save_session(SessionPayload(
                session_id=session_id,
                model=current_model,
                agent=current_agent,
                conversations=conversations,
            ))
            print()

        except (KeyboardInterrupt, EOFError):
            print()
            break
        except Exception as err:
            print(f"\n  {BG_RED}{WHITE} Error {RESET} {RED}{err}{RESET}")


if __name__ == "__main__":
    main()
