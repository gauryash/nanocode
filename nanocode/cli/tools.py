"""Tool definitions, implementations, validation, and schema builders."""

import json

from nanocode.permission import PermissionManager
from nanocode.cli.config import AGENT_TOOLS
from nanocode.cli.ui import DIM, GRAY, RESET, _BOX

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


# --- Tool definitions ---

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


def parse_tool_args(raw):
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {}


# --- Validation ---


def validate_tool_args(name, args):
    """Validate *args* against the declared schema for tool *name*.

    Returns an error string or None if valid.
    """
    if name not in TOOLS:
        return f"unknown tool '{name}'"

    _desc, params, _fn = TOOLS[name]
    for param_name, param_type in params.items():
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
        if key not in params:
            return f"unexpected argument '{key}' for tool '{name}'"

    return None


def run_tool(name, args, agent_id=None):
    if agent_id and agent_id in AGENT_TOOLS and name not in AGENT_TOOLS[agent_id]:
        return f"error: tool '{name}' is not available for agent '{agent_id}'"
    error = validate_tool_args(name, args)
    if error:
        return f"error: {error}"
    try:
        return TOOLS[name][2](args)
    except Exception as err:
        return f"error: {err}"


# --- Schema builders ---


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
