"""Configuration constants and environment setup for the CLI."""

import os
from pathlib import Path

from nanocode.permission.fs_wrapper import FileSystemWrapper

# Framework-global FileSystemWrapper (trusted — used for NanoCode's own files)
_fs: FileSystemWrapper = FileSystemWrapper()


# --- inline .env loader (zero deps) ---


def _load_dotenv(path=".env"):
    """Load KEY=VALUE pairs from a .env file.  Does NOT override existing env vars.

    This is a framework operation (not an agent action).
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

    Prefers OPENCODE_GO_API_KEY over OPENCODE_API_KEY for backward compat.
    """
    return os.environ.get("OPENCODE_GO_API_KEY") or os.environ.get("OPENCODE_API_KEY")


_PACKAGE_DIR = Path(__file__).resolve().parent.parent

MODELS_URL = "https://opencode.ai/zen/go/v1/models"
CHAT_COMPLETIONS_URL = "https://opencode.ai/zen/go/v1/chat/completions"
MESSAGES_URL = "https://opencode.ai/zen/go/v1/messages"
DEFAULT_MODEL = "deepseek-v4-flash"
MODEL = os.environ.get("MODEL", DEFAULT_MODEL)
MAX_TOKENS = int(os.environ.get("MAX_TOKENS", "8192"))
HTTP_TIMEOUT = int(os.environ.get("HTTP_TIMEOUT", "60"))

DEFAULT_AGENT = os.environ.get("AGENT", "coder")
AGENTS_DIR = os.environ.get("AGENTS_DIR", "agents")
SESSIONS_DIR = os.path.join(os.getcwd(), ".nanocode", "sessions")
SYSTEM_PROMPT_PATH = os.environ.get(
    "SYSTEM_PROMPT_PATH",
    str(_PACKAGE_DIR / "system.md")
)

AGENT_FILES = {
    "coder": "coder.md",
    "architect": "architect.md",
    "reviewer": "reviewer.md",
    "debugger": "debugger.md",
    "tester": "tester.md",
    "refactor": "refactor.md",
}

AGENT_TOOLS = {
    "coder":     {"read", "write", "edit", "glob", "grep", "bash"},
    "architect": {"read", "glob", "grep"},
    "reviewer":  {"read", "glob", "grep"},
    "debugger":  {"read", "glob", "grep", "bash"},
    "tester":    {"read", "glob", "grep"},
    "refactor":  {"read", "glob", "grep"},
}

ANTHROPIC_COMPAT_MODELS = {
    "minimax-m3",
    "minimax-m2.7",
    "minimax-m2.5",
    "qwen3.7-max",
    "qwen3.7-plus",
    "qwen3.6-plus",
    "qwen3.5-plus",
}


