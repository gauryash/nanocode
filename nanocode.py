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
  /help             show commands
"""

import glob as globlib
import json
import os
import re
import shutil
import subprocess
import urllib.error
import urllib.request

OPENCODE_GO_KEY = os.environ.get("OPENCODE_GO_API_KEY") or os.environ.get("OPENCODE_API_KEY")
MODELS_URL = "https://opencode.ai/zen/go/v1/models"
CHAT_COMPLETIONS_URL = "https://opencode.ai/zen/go/v1/chat/completions"
MESSAGES_URL = "https://opencode.ai/zen/go/v1/messages"
DEFAULT_MODEL = "deepseek-v4-flash"
MODEL = os.environ.get("MODEL", DEFAULT_MODEL)
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "8192"))

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

# ANSI colors
RESET, BOLD, DIM = "\033[0m", "\033[1m", "\033[2m"
BLUE, CYAN, GREEN, YELLOW, RED = (
    "\033[34m",
    "\033[36m",
    "\033[32m",
    "\033[33m",
    "\033[31m",
)


# --- Tool implementations ---


def read(args):
    with open(args["path"], "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
    offset = int(args.get("offset", 0))
    limit = int(args.get("limit", len(lines)))
    selected = lines[offset : offset + limit]
    return "".join(f"{offset + idx + 1:4}| {line}" for idx, line in enumerate(selected))


def write(args):
    with open(args["path"], "w", encoding="utf-8") as f:
        f.write(args["content"])
    return "ok"


def edit(args):
    with open(args["path"], "r", encoding="utf-8", errors="replace") as f:
        text = f.read()
    old, new = args["old"], args["new"]
    if old not in text:
        return "error: old_string not found"
    count = text.count(old)
    if not args.get("all") and count > 1:
        return f"error: old_string appears {count} times, must be unique (use all=true)"
    replacement = text.replace(old, new) if args.get("all") else text.replace(old, new, 1)
    with open(args["path"], "w", encoding="utf-8") as f:
        f.write(replacement)
    return "ok"


def glob(args):
    pattern = (args.get("path", ".") + "/" + args["pat"]).replace("//", "/")
    files = globlib.glob(pattern, recursive=True)
    files = sorted(
        files,
        key=lambda f: os.path.getmtime(f) if os.path.isfile(f) else 0,
        reverse=True,
    )
    return "\n".join(files) or "none"


def grep(args):
    pattern = re.compile(args["pat"])
    hits = []
    root = args.get("path", ".")
    for filepath in globlib.glob(root + "/**", recursive=True):
        if not os.path.isfile(filepath):
            continue
        try:
            with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                for line_num, line in enumerate(f, 1):
                    if pattern.search(line):
                        hits.append(f"{filepath}:{line_num}:{line.rstrip()}")
                        if len(hits) >= 50:
                            return "\n".join(hits)
        except Exception:
            pass
    return "\n".join(hits) or "none"


def bash(args):
    proc = subprocess.Popen(
        args["cmd"],
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    output_lines = []
    try:
        while True:
            line = proc.stdout.readline()
            if not line and proc.poll() is not None:
                break
            if line:
                print(f"  {DIM}| {line.rstrip()}{RESET}", flush=True)
                output_lines.append(line)
        proc.wait(timeout=30)
    except subprocess.TimeoutExpired:
        proc.kill()
        output_lines.append("\n(timed out after 30s)")
    return "".join(output_lines).strip() or "(empty)"


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


def run_tool(name, args):
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


def make_anthropic_schema():
    result = []
    for name, (description, params, _fn) in TOOLS.items():
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


def make_openai_schema():
    result = []
    for name, (description, params, _fn) in TOOLS.items():
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
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers=headers or {})
    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {err.code}: {body}") from err


def fetch_models():
    response = http_json(MODELS_URL, headers=auth_headers(require_key=False))
    return [item["id"] for item in response.get("data", [])]


def call_openai_api(messages, system_prompt, model):
    payload = {
        "model": strip_opencode_prefix(model),
        "max_tokens": MAX_TOKENS,
        "messages": [{"role": "system", "content": system_prompt}] + messages,
        "tools": make_openai_schema(),
        "tool_choice": "auto",
    }
    return http_json(CHAT_COMPLETIONS_URL, payload, auth_headers(require_key=True))


def call_anthropic_api(messages, system_prompt, model):
    payload = {
        "model": strip_opencode_prefix(model),
        "max_tokens": MAX_TOKENS,
        "system": system_prompt,
        "messages": messages,
        "tools": make_anthropic_schema(),
    }
    headers = auth_headers(require_key=True, extra={"anthropic-version": "2023-06-01"})
    return http_json(MESSAGES_URL, payload, headers)


def separator():
    cols = shutil.get_terminal_size((80, 20)).columns
    return f"{DIM}{'-' * min(cols, 80)}{RESET}"


def render_markdown(text):
    return re.sub(r"\*\*(.+?)\*\*", f"{BOLD}\\1{RESET}", text)


def print_help(current_model):
    print(
        f"""{BOLD}Commands{RESET}
  /q, exit          quit
  /c                clear conversation
  /models           fetch and list OpenCode Go models
  /model            show current model
  /model <id|num>   switch model; clears conversation
  /help             show this help

{BOLD}Current model{RESET}: {current_model} ({endpoint_kind(current_model)})"""
    )


def print_tool_call(tool_name, tool_args):
    values = list(tool_args.values()) if isinstance(tool_args, dict) else []
    arg_preview = str(values[0])[:50] if values else ""
    print(f"\n{GREEN}> {tool_name}{RESET}({DIM}{arg_preview}{RESET})")


def print_tool_result(result):
    result_lines = result.split("\n")
    preview = result_lines[0][:60] if result_lines else ""
    if len(result_lines) > 1:
        preview += f" ... +{len(result_lines) - 1} lines"
    elif result_lines and len(result_lines[0]) > 60:
        preview += "..."
    print(f"  {DIM}`- {preview}{RESET}")


def parse_tool_args(raw):
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


def run_openai_turn(messages, system_prompt, model):
    response = call_openai_api(messages, system_prompt, model)
    message = response.get("choices", [{}])[0].get("message", {})

    content = message.get("content") or ""
    if content:
        print(f"\n{CYAN}>{RESET} {render_markdown(content)}")

    assistant_message = {"role": "assistant", "content": content}
    tool_calls = message.get("tool_calls") or []
    if tool_calls:
        assistant_message["tool_calls"] = tool_calls
    messages.append(assistant_message)

    if not tool_calls:
        return False

    for tool_call in tool_calls:
        function = tool_call.get("function", {})
        tool_name = function.get("name", "")
        tool_args = parse_tool_args(function.get("arguments"))
        print_tool_call(tool_name, tool_args)
        result = run_tool(tool_name, tool_args)
        print_tool_result(result)
        messages.append(
            {
                "role": "tool",
                "tool_call_id": tool_call.get("id"),
                "name": tool_name,
                "content": result,
            }
        )
    return True


def run_anthropic_turn(messages, system_prompt, model):
    response = call_anthropic_api(messages, system_prompt, model)
    content_blocks = response.get("content", [])
    tool_results = []

    for block in content_blocks:
        if block.get("type") == "text":
            print(f"\n{CYAN}>{RESET} {render_markdown(block.get('text', ''))}")

        if block.get("type") == "tool_use":
            tool_name = block.get("name", "")
            tool_args = block.get("input", {})
            print_tool_call(tool_name, tool_args)
            result = run_tool(tool_name, tool_args)
            print_tool_result(result)
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.get("id"),
                    "content": result,
                }
            )

    messages.append({"role": "assistant", "content": content_blocks})

    if not tool_results:
        return False

    messages.append({"role": "user", "content": tool_results})
    return True


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
        print(f"{YELLOW}> Warning: {arg!r} was not in /models; trying it anyway.{RESET}")
    return arg


def main():
    current_model = strip_opencode_prefix(MODEL)
    model_cache = []
    messages = []
    system_prompt = f"Concise coding assistant. cwd: {os.getcwd()}"

    print(
        f"{BOLD}nanocode-go{RESET} | {DIM}{current_model} "
        f"({endpoint_kind(current_model)}) | {os.getcwd()}{RESET}\n"
    )

    while True:
        try:
            print(separator())
            user_input = input(f"{BOLD}{BLUE}>{RESET} ").strip()
            print(separator())
            if not user_input:
                continue

            if user_input in ("/q", "exit"):
                break

            if user_input == "/help":
                print_help(current_model)
                continue

            if user_input == "/c":
                messages = []
                print(f"{GREEN}> Cleared conversation{RESET}")
                continue

            if user_input == "/models":
                model_cache = fetch_models()
                for i, model_id in enumerate(model_cache, 1):
                    marker = "*" if model_id == current_model else " "
                    print(f"{marker} {i:2}. {model_id} ({endpoint_kind(model_id)})")
                continue

            if user_input == "/model":
                print(f"{GREEN}> Current model: {current_model} ({endpoint_kind(current_model)}){RESET}")
                continue

            if user_input.startswith("/model ") or user_input.startswith("/m "):
                _, raw_model = user_input.split(maxsplit=1)
                new_model = choose_model(raw_model, model_cache)
                if new_model != current_model:
                    current_model = new_model
                    messages = []
                    print(
                        f"{GREEN}> Switched to {current_model} "
                        f"({endpoint_kind(current_model)}); cleared conversation{RESET}"
                    )
                else:
                    print(f"{GREEN}> Already using {current_model}{RESET}")
                continue

            messages.append({"role": "user", "content": user_input})

            # Agentic loop: keep calling API until no more tool calls.
            while True:
                kind = endpoint_kind(current_model)
                if kind == "anthropic":
                    has_more_tools = run_anthropic_turn(messages, system_prompt, current_model)
                else:
                    has_more_tools = run_openai_turn(messages, system_prompt, current_model)
                if not has_more_tools:
                    break

            print()

        except (KeyboardInterrupt, EOFError):
            break
        except Exception as err:
            print(f"{RED}> Error: {err}{RESET}")


if __name__ == "__main__":
    main()
