"""Configuration constants and environment setup for the CLI.

All environment variable loading happens once at import time.
Validation at this boundary ensures downstream code never sees invalid config.
"""

from __future__ import annotations

import os
from pathlib import Path

from nanocode.permission.fs_wrapper import FileSystemWrapper
from nanocode.cli.skill_loader import discover_skills, build_skill_config

__all__ = [
    "_fs", "_get_api_key",
    "MODELS_URL", "CHAT_COMPLETIONS_URL", "MESSAGES_URL",
    "DEFAULT_MODEL", "MODEL", "MAX_TOKENS", "HTTP_TIMEOUT",
    "SESSIONS_DIR", "SYSTEM_PROMPT_PATH",
    "SKILLS_DIR",
    "AGENT_FILES", "AGENT_TOOLS", "ANTHROPIC_COMPAT_MODELS",
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

SKILLS_DIR = os.environ.get("SKILLS_DIR", "skills")

_skills = discover_skills(SKILLS_DIR)
AGENT_FILES: dict[str, str]
AGENT_TOOLS: dict[str, set[str]]
AGENT_FILES, AGENT_TOOLS = build_skill_config(_skills)

ANTHROPIC_COMPAT_MODELS: set[str] = {
    "minimax-m3",
    "minimax-m2.7",
    "minimax-m2.5",
    "qwen3.7-max",
    "qwen3.7-plus",
    "qwen3.6-plus",
    "qwen3.5-plus",
}
