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

import os
from pathlib import Path

from nanocode.cli.config import (
    MODEL, DEFAULT_MODEL, DEFAULT_AGENT, AGENTS_DIR,
    AGENT_FILES, AGENT_TOOLS,
    _fs, _get_api_key,
)
from nanocode.cli.tools import init_permission_manager, TOOLS
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
    _new_session_id, save_session, load_session, list_sessions, _resolve_session_id,
)


# --- Agent prompt system ---


def load_agent_prompt(agent_id):
    if agent_id not in AGENT_FILES:
        raise ValueError(f"unknown agent {agent_id!r}")

    path = Path(AGENTS_DIR) / AGENT_FILES[agent_id]

    template = _fs.read_text(path)

    return template.format(cwd=os.getcwd())


def list_agents():
    return list(AGENT_FILES.keys())


def load_system_prompt():
    """Load the base system prompt from nanocode/system.md (optional)."""
    from nanocode.cli.config import SYSTEM_PROMPT_PATH
    try:
        return _fs.read_text(Path(SYSTEM_PROMPT_PATH)).strip()
    except FileNotFoundError:
        return ""


def agent_system_prompt(agent_id):
    agent_prompt = load_agent_prompt(agent_id)
    system_prompt = load_system_prompt()
    if system_prompt:
        return system_prompt + "\n\n" + agent_prompt
    return agent_prompt


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


def choose_model(arg, model_cache):
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


def main():
    current_model = MODEL.removeprefix("opencode-go/").strip()
    model_cache = []
    current_agent = DEFAULT_AGENT if DEFAULT_AGENT in AGENT_FILES else "coder"
    conversations = {agent_id: [] for agent_id in AGENT_FILES}
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
                save_session(session_id, conversations, current_model, current_agent)
                break

            if user_input == "/help":
                print_help(current_model, current_agent)
                continue

            if user_input == "/c":
                conversations = {agent_id: [] for agent_id in AGENT_FILES}
                save_session(session_id, conversations, current_model, current_agent)
                print(f"  {GREEN}\u2713 Cleared all conversations{RESET}")
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
                    marker = "*" if s["id"] == session_id else " "
                    print(
                        f"{DIM}{_BOX['v']}{RESET} {marker} {BOLD if marker == '*' else ''}{s['id']}{RESET}"
                        f"  {GRAY}{s['model']} \u00b7 {s['agent']} \u00b7 {s['messages']} msgs"
                        f" \u00b7 {s['updated']}{RESET}"
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
                print(f"  {GREEN}\u2713 New session{RESET}  {BOLD}{session_id}{RESET}")
                continue

            if user_input.startswith("/session "):
                _, raw_sid = user_input.split(maxsplit=1)
                try:
                    target_id = _resolve_session_id(raw_sid)
                    save_session(session_id, conversations, current_model, current_agent)
                    conversations, restored_model, restored_agent = load_session(target_id)
                    for agent_id in AGENT_FILES:
                        conversations.setdefault(agent_id, [])
                    session_id = target_id
                    if restored_model:
                        current_model = restored_model
                    if restored_agent and restored_agent in AGENT_FILES:
                        current_agent = restored_agent
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
            save_session(session_id, conversations, current_model, current_agent)
            print()

        except (KeyboardInterrupt, EOFError):
            print()
            break
        except Exception as err:
            print(f"\n  {BG_RED}{WHITE} Error {RESET} {RED}{err}{RESET}")


if __name__ == "__main__":
    main()
