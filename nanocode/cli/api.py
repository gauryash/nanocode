"""API client — HTTP calls, auth, model fetching, API interaction loops.

Third-party API responses are validated as untrusted data at the boundary
before being used in any logic or rendering.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

from nanocode.cli.config import (
    MODELS_URL, CHAT_COMPLETIONS_URL, MESSAGES_URL,
    MAX_TOKENS, HTTP_TIMEOUT, AGENT_TOOLS, _get_api_key,
)
from nanocode.cli.tools import make_openai_schema, make_anthropic_schema, run_tool, parse_tool_args
from nanocode.cli.types import Ok, Err
from nanocode.cli.ui import (
    _spinner_start, _spinner_stop,
    _render_text_block, print_tool_call, print_tool_result,
)

__all__ = [
    "auth_headers", "http_json",
    "fetch_models",
    "call_openai_api", "call_anthropic_api",
    "run_openai_turn", "run_anthropic_turn",
]


def auth_headers(require_key: bool = True, extra: dict[str, str] | None = None) -> dict[str, str]:
    key = _get_api_key()
    if require_key and not key:
        raise RuntimeError("Set OPENCODE_GO_API_KEY before making model requests.")
    headers = {"Content-Type": "application/json", "User-Agent": "nanocode-go/1.0"}
    if key:
        headers["Authorization"] = f"Bearer {key}"
    if extra:
        headers.update(extra)
    return headers


def http_json(url: str, payload: dict | None = None, headers: dict | None = None) -> dict:
    """Make an HTTP JSON request. Raises ``RuntimeError`` on failure."""
    _spinner_start()
    try:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url, data=data, headers=headers or {})
        try:
            with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT) as response:
                body: dict = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as err:
            body = err.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {err.code}: {body}") from err
        except urllib.error.URLError as err:
            raise RuntimeError(f"Request failed (timeout={HTTP_TIMEOUT}s): {err.reason}") from err
    finally:
        _spinner_stop()
    return body


def fetch_models() -> list[str]:
    """Fetch available models from the API.

    Validates the response shape at the boundary — ``data`` must be a list
    of objects with an ``id`` string field.
    """
    response = http_json(MODELS_URL, headers=auth_headers(require_key=False))
    raw_data = response.get("data")
    if not isinstance(raw_data, list):
        raise RuntimeError(f"unexpected API response: 'data' is not a list ({type(raw_data).__name__})")
    ids: list[str] = []
    for item in raw_data:
        if not isinstance(item, dict):
            continue
        mid = item.get("id")
        if isinstance(mid, str):
            ids.append(mid)
    return ids


def call_openai_api(messages: list, system_prompt: str, model: str, allowed_tools: set[str] | None = None) -> dict:
    payload = {
        "model": model.removeprefix("opencode-go/").strip(),
        "max_tokens": MAX_TOKENS,
        "messages": [{"role": "system", "content": system_prompt}] + messages,
        "tools": make_openai_schema(allowed_tools),
        "tool_choice": "auto",
    }
    return http_json(CHAT_COMPLETIONS_URL, payload, auth_headers(require_key=True))


def call_anthropic_api(messages: list, system_prompt: str, model: str, allowed_tools: set[str] | None = None) -> dict:
    payload = {
        "model": model.removeprefix("opencode-go/").strip(),
        "max_tokens": MAX_TOKENS,
        "system": system_prompt,
        "messages": messages,
        "tools": make_anthropic_schema(allowed_tools),
    }
    headers = auth_headers(require_key=True, extra={"anthropic-version": "2023-06-01"})
    return http_json(MESSAGES_URL, payload, headers)


def run_openai_turn(messages: list, system_prompt: str, model: str, agent_id: str | None = None) -> tuple[bool, float]:
    allowed_tools = AGENT_TOOLS.get(agent_id) if agent_id else None
    t0 = time.time()
    response = call_openai_api(messages, system_prompt, model, allowed_tools)
    choices = response.get("choices")
    message = choices[0].get("message", {}) if isinstance(choices, list) and choices else {}

    content = message.get("content") or ""
    if content:
        print(f"\n{_render_text_block(content)}")

    assistant_message: dict = {"role": "assistant", "content": content}
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
                "content": result.message if isinstance(result, (Ok, Err)) else str(result),
            }
        )
    return True, time.time() - t0


def run_anthropic_turn(messages: list, system_prompt: str, model: str, agent_id: str | None = None) -> tuple[bool, float]:
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
                    "content": result.message if isinstance(result, (Ok, Err)) else str(result),
                }
            )

    messages.append({"role": "assistant", "content": content_blocks})

    if not tool_results:
        return False, time.time() - t0

    messages.append({"role": "user", "content": tool_results})
    return True, time.time() - t0
