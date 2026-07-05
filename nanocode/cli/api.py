"""API client — HTTP calls, auth, model fetching, API interaction loops.

Third-party API responses are validated as untrusted data at the boundary
before being used in any logic or rendering.
"""

from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.request

from nanocode.cli.config import (
    MODELS_URL, CHAT_COMPLETIONS_URL, MESSAGES_URL,
    MAX_TOKENS, HTTP_TIMEOUT, _get_api_key,
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
    "classify_skill",
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


def run_openai_turn(messages: list, system_prompt: str, model: str, allowed_tools: set[str] | None = None) -> tuple[bool, float]:
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
        result = run_tool(tool_name, tool_args)
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


def run_anthropic_turn(messages: list, system_prompt: str, model: str, allowed_tools: set[str] | None = None) -> tuple[bool, float]:
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
            result = run_tool(tool_name, tool_args)
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


# ---------------------------------------------------------------------------
# Skill classification — matches a user message against the skill catalog
# ---------------------------------------------------------------------------

_CLASSIFY_SYSTEM_PROMPT = """You are a skill classifier. Given a user message and a list of available skills, select the single best-matching skill. Respond with a JSON object only:

{"skill": "skill-name", "confidence": 0.0-1.0}

Rules:
- "skill" must be one of the listed skill names (exact match), or null if none match well.
- "confidence" is your certainty: 1.0 = perfect match, 0.0 = no match.
- Only suggest a skill if the user's request clearly falls in its domain.
- Be precise — don't guess. Return null if unsure."""


def _keyword_prefilter(user_message: str, catalog: dict[str, str], top_n: int = 30) -> dict[str, str]:
    """Quick keyword match to narrow the candidate pool before the LLM call."""
    words = set()
    for w in re.findall(r"[a-zA-Z_][a-zA-Z_0-9]{2,}", user_message):
        words.add(w.lower())
    if not words:
        return dict(list(catalog.items())[:top_n])

    scored: list[tuple[int, str, str]] = []
    for name, desc in catalog.items():
        score = 0
        name_lower = name.lower()
        desc_lower = desc.lower()
        for w in words:
            if w in name_lower:
                score += 3
            elif w in desc_lower:
                score += 1
        if score > 0:
            scored.append((score, name, desc))

    scored.sort(key=lambda x: -x[0])
    return {name: desc for _, name, desc in scored[:top_n]}


def classify_skill(
    user_message: str,
    catalog: dict[str, str],
    model: str,
) -> tuple[str | None, float]:
    """Ask the LLM which skill best matches *user_message*.

    Returns ``(skill_name, confidence)`` or ``(None, 0.0)``.
    """
    if not catalog or not user_message:
        return None, 0.0

    candidates = _keyword_prefilter(user_message, catalog)
    if not candidates:
        return None, 0.0

    skills_block = "\n".join(f"- {name}: {desc}" for name, desc in candidates.items())
    user_payload = (
        f"Candidate skills:\n{skills_block}\n\n"
        f"User message: {user_message}"
    )

    payload = {
        "model": model.removeprefix("opencode-go/").strip(),
        "max_tokens": 100,
        "messages": [
            {"role": "system", "content": _CLASSIFY_SYSTEM_PROMPT},
            {"role": "user", "content": user_payload},
        ],
    }

    kind = "anthropic" if (model in _anthropic_compat() or model.startswith("minimax-") or model.startswith("qwen")) else "openai"

    try:
        if kind == "anthropic":
            payload["system"] = payload["messages"].pop(0)["content"]
            payload["messages"] = payload["messages"]
            response = http_json(MESSAGES_URL, payload, auth_headers(require_key=True, extra={"anthropic-version": "2023-06-01"}))
            content_blocks = response.get("content", [])
            raw = ""
            for block in content_blocks:
                if block.get("type") == "text":
                    raw = block.get("text", "")
                    break
        else:
            response = http_json(CHAT_COMPLETIONS_URL, payload, auth_headers(require_key=True))
            choices = response.get("choices")
            raw = choices[0].get("message", {}).get("content", "") if isinstance(choices, list) and choices else ""

        if not raw:
            return None, 0.0

        data = json.loads(raw.strip())
        skill = data.get("skill")
        confidence = float(data.get("confidence", 0.0))
        if skill and skill in catalog:
            return skill, confidence
        return None, 0.0

    except Exception:
        return None, 0.0


def _anthropic_compat() -> set[str]:
    """Lazy import to avoid circular dependency."""
    from nanocode.cli.config import ANTHROPIC_COMPAT_MODELS
    return ANTHROPIC_COMPAT_MODELS
