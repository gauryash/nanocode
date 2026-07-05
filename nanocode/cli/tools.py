"""Tool definitions, implementations, validation, and schema builders."""

from __future__ import annotations

import json
from typing import Callable, NamedTuple

from nanocode.permission import PermissionManager
from nanocode.cli.config import AGENT_TOOLS
from nanocode.cli.ui import DIM, GRAY, RESET, _BOX
from nanocode.cli.types import ToolResult, Ok, Err

__all__ = [
    "ToolDef", "TOOLS",
    "init_permission_manager", "get_permission_manager",
    "validate_tool_args", "run_tool", "parse_tool_args",
    "make_openai_schema", "make_anthropic_schema",
]


Params = dict[str, str]
ToolFn = Callable[[dict], ToolResult]


class ToolDef(NamedTuple):
    """Definition of a tool available to the LLM agent."""

    description: str
    params: Params
    fn: ToolFn


_pm: PermissionManager | None = None


def init_permission_manager():
    """Initialize the global PermissionManager from the CWD."""
    from pathlib import Path
    global _pm
    _pm = PermissionManager(Path.cwd())
    return _pm


def get_permission_manager() -> PermissionManager:
    assert _pm is not None, "PermissionManager not initialized"
    return _pm


# --- Tool implementations ---


def _read(args: dict) -> ToolResult:
    pm = get_permission_manager()
    path = args["path"]
    offset = int(args.get("offset", 0))
    limit = int(args["limit"]) if args.get("limit") is not None else None
    try:
        return Ok(pm.read_text(path, reason="Agent requested file read", offset=offset, limit=limit))
    except PermissionError as e:
        return Err(str(e))


def _write(args: dict) -> ToolResult:
    pm = get_permission_manager()
    path = args["path"]
    content = args["content"]
    try:
        pm.write_text(path, content, reason="Agent requested file write")
        return Ok("ok")
    except PermissionError as e:
        return Err(str(e))


def _edit(args: dict) -> ToolResult:
    pm = get_permission_manager()
    path = args["path"]
    old = args["old"]
    new = args["new"]
    all_occurrences = args.get("all", False)
    try:
        result = pm.edit_text(path, old, new, all_occurrences, reason="Agent requested file edit")
        return Ok(result)
    except PermissionError as e:
        return Err(str(e))


def _glob(args: dict) -> ToolResult:
    pm = get_permission_manager()
    pattern = args["pat"]
    root = args.get("path", ".")
    try:
        return Ok(pm.glob(pattern, root, reason="Agent requested file search"))
    except PermissionError as e:
        return Err(str(e))


def _grep(args: dict) -> ToolResult:
    pm = get_permission_manager()
    pattern = args["pat"]
    root = args.get("path", ".")
    try:
        return Ok(pm.grep(pattern, root, reason="Agent requested text search"))
    except PermissionError as e:
        return Err(str(e))


def _bash(args: dict) -> ToolResult:
    pm = get_permission_manager()
    command = args["cmd"]
    try:
        def stream(line):
            print(f"  {DIM}{_BOX['v']}{RESET} {line}", flush=True)
        result = pm.run_command(command, reason="Agent requested shell command", line_callback=stream)
        return Ok(result)
    except PermissionError as e:
        return Err(str(e))


# --- Tool definitions ---

TOOLS: dict[str, ToolDef] = {
    "read": ToolDef(
        "Read file with line numbers (file path, not directory)",
        {"path": "string", "offset": "number?", "limit": "number?"},
        _read,
    ),
    "write": ToolDef(
        "Write content to file",
        {"path": "string", "content": "string"},
        _write,
    ),
    "edit": ToolDef(
        "Replace old with new in file (old must be unique unless all=true)",
        {"path": "string", "old": "string", "new": "string", "all": "boolean?"},
        _edit,
    ),
    "glob": ToolDef(
        "Find files by pattern, sorted by mtime",
        {"pat": "string", "path": "string?"},
        _glob,
    ),
    "grep": ToolDef(
        "Search files for regex pattern",
        {"pat": "string", "path": "string?"},
        _grep,
    ),
    "bash": ToolDef(
        "Run shell command",
        {"cmd": "string"},
        _bash,
    ),
}


def parse_tool_args(raw: str | dict | None) -> dict:
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


# --- Validation ---


def validate_tool_args(name: str, args: dict) -> str | None:
    """Validate *args* against the declared schema for tool *name*.

    Returns an error string or None if valid.
    """
    if name not in TOOLS:
        return f"unknown tool '{name}'"

    tool = TOOLS[name]
    for param_name, param_type in tool.params.items():
        is_optional = param_type.endswith("?")
        if param_name not in args:
            if not is_optional:
                return f"missing required argument '{param_name}' for tool '{name}'"
            continue

        value = args[param_name]
        base_type = param_type.rstrip("?")

        if base_type == "string":
            if not isinstance(value, str):
                return f"argument '{param_name}' for tool '{name}' must be a string, got {type(value).__name__}"
        elif base_type == "number":
            if not isinstance(value, (int, float)):
                return f"argument '{param_name}' for tool '{name}' must be a number, got {type(value).__name__}"
        elif base_type == "boolean":
            if not isinstance(value, bool):
                return f"argument '{param_name}' for tool '{name}' must be a boolean, got {type(value).__name__}"

    for key in args:
        if key not in tool.params:
            return f"unexpected argument '{key}' for tool '{name}'"

    return None


def run_tool(name: str, args: dict, agent_id: str | None = None) -> ToolResult:
    if agent_id and agent_id in AGENT_TOOLS and name not in AGENT_TOOLS[agent_id]:
        return Err(f"tool '{name}' is not available for agent '{agent_id}'")
    error = validate_tool_args(name, args)
    if error:
        return Err(error)
    try:
        return TOOLS[name].fn(args)
    except Exception as err:
        return Err(str(err))


# --- Schema builders ---


def json_type(param_type: str) -> str:
    base_type = param_type.rstrip("?")
    if base_type == "number":
        return "integer"
    return base_type


def make_properties(params: Params) -> tuple[dict, list[str]]:
    properties = {}
    required = []
    for param_name, param_type in params.items():
        is_optional = param_type.endswith("?")
        properties[param_name] = {"type": json_type(param_type)}
        if not is_optional:
            required.append(param_name)
    return properties, required


def make_anthropic_schema(allowed_tools: set[str] | None = None) -> list[dict]:
    result = []
    tools = TOOLS if allowed_tools is None else {k: v for k, v in TOOLS.items() if k in allowed_tools}
    for name, tool in tools.items():
        properties, required = make_properties(tool.params)
        result.append(
            {
                "name": name,
                "description": tool.description,
                "input_schema": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            }
        )
    return result


def make_openai_schema(allowed_tools: set[str] | None = None) -> list[dict]:
    result = []
    tools = TOOLS if allowed_tools is None else {k: v for k, v in TOOLS.items() if k in allowed_tools}
    for name, tool in tools.items():
        properties, required = make_properties(tool.params)
        result.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": tool.description,
                    "parameters": {
                        "type": "object",
                        "properties": properties,
                        "required": required,
                    },
                },
            }
        )
    return result
