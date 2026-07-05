"""Configuration constants and environment setup for the CLI.

All environment variable loading happens once at import time.
Validation at this boundary ensures downstream code never sees invalid config.
"""

from __future__ import annotations

import os
from pathlib import Path

from nanocode.permission.fs_wrapper import FileSystemWrapper
from nanocode.cli.catalog import load_catalog, SKILL_CATALOG
from nanocode.cli.skill_loader import discover_skills, discover_skill_files, build_skill_config, NATIVE_TOOLS

__all__ = [
    "_fs", "_get_api_key",
    "MODELS_URL", "CHAT_COMPLETIONS_URL", "MESSAGES_URL",
    "DEFAULT_MODEL", "MODEL", "MAX_TOKENS", "HTTP_TIMEOUT",
    "SESSIONS_DIR", "SYSTEM_PROMPT_PATH",
    "SKILLS_DIR",
    "AGENT_FILES", "AGENT_TOOLS", "ANTHROPIC_COMPAT_MODELS",
    "SKILL_CATALOG",
    "_PACKAGE_DIR",
]

_fs: FileSystemWrapper = FileSystemWrapper()


def _load_dotenv(path: str = ".env") -> None:
    """Load KEY=VALUE pairs from a .env file.

    Does NOT override existing env vars. This is a framework operation,
    not an agent action.
    """
    try:
        env_path = Path(path).resolve()
        content = _fs.read_text(env_path)
        for line in content.split("\n"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key, value = key.strip(), value.strip()
            if key and key not in os.environ:
                os.environ[key] = value
    except FileNotFoundError:
        pass
    except OSError:
        pass


_load_dotenv()


def _get_api_key() -> str | None:
    """Read the API key from environment on demand.

    Prefers ``OPENCODE_GO_API_KEY``; falls back to ``OPENCODE_API_KEY``.
    """
    return os.environ.get("OPENCODE_GO_API_KEY") or os.environ.get("OPENCODE_API_KEY")


def _env_int(key: str, default: int) -> int:
    """Parse an integer env var or crash with a clear message."""
    raw = os.environ.get(key)
    if raw is None:
        return default
    try:
        return int(raw)
    except ValueError:
        raise RuntimeError(
            f"Environment variable {key} must be an integer, got {raw!r}"
        )


_PACKAGE_DIR = Path(__file__).resolve().parent.parent

MODELS_URL = "https://opencode.ai/zen/go/v1/models"
CHAT_COMPLETIONS_URL = "https://opencode.ai/zen/go/v1/chat/completions"
MESSAGES_URL = "https://opencode.ai/zen/go/v1/messages"
DEFAULT_MODEL = "deepseek-v4-flash"
MODEL = os.environ.get("MODEL", DEFAULT_MODEL)
MAX_TOKENS = _env_int("MAX_TOKENS", 8192)
HTTP_TIMEOUT = _env_int("HTTP_TIMEOUT", 60)

SESSIONS_DIR = os.path.join(os.getcwd(), ".nanocode", "sessions")
SYSTEM_PROMPT_PATH = os.environ.get(
    "SYSTEM_PROMPT_PATH",
    str(_PACKAGE_DIR / "system.md"),
)

# Priority: SKILLS_DIR env var > CWD skills/ > bundled package skills
_BUNDLED_SKILLS = str(_PACKAGE_DIR / "skills")
_CWD_SKILLS = os.path.join(os.getcwd(), "skills")
SKILLS_DIR = (
    os.environ.get("SKILLS_DIR")
    or (_CWD_SKILLS if os.path.isdir(_CWD_SKILLS) else _BUNDLED_SKILLS)
)

# --- Catalog (from agent-skills.md) → skill_name : description ---
_catalog_path = Path(SKILLS_DIR) / "agent-skills.md"
if _catalog_path.is_file():
    try:
        SKILL_CATALOG.update(load_catalog(_catalog_path))
    except Exception:
        pass  # Non-fatal — skills still work, just without descriptions

# --- File discovery (recursive) → skill_name : relative_path ---
_skill_files = discover_skill_files(SKILLS_DIR)

# --- Merge: build AGENT_FILES from catalog names + discovered files ---
AGENT_FILES: dict[str, str] = {}
AGENT_TOOLS: dict[str, set[str]] = {}

# Match catalog names to discovered files
for name in SKILL_CATALOG:
    path = _skill_files.get(name)
    if path:
        AGENT_FILES[name] = path
    # else: catalog entry without a matching file — skip (can't load the prompt)

# Every skill gets the full native tool set by default
for name in AGENT_FILES:
    AGENT_TOOLS[name] = set(NATIVE_TOOLS)

# Also run legacy flat discover for backward compat (frontmatter tools)
_skills = discover_skills(SKILLS_DIR)
_legacy_files, _legacy_tools = build_skill_config(_skills)
# Legacy tool restrictions override the default full set
for name, tools in _legacy_tools.items():
    if name in AGENT_TOOLS:
        AGENT_TOOLS[name] = tools

ANTHROPIC_COMPAT_MODELS: set[str] = {
    "minimax-m3",
    "minimax-m2.7",
    "minimax-m2.5",
    "qwen3.7-max",
    "qwen3.7-plus",
    "qwen3.6-plus",
    "qwen3.5-plus",
}
