"""PermissionManager — the security boundary for all filesystem operations.

No code outside this module should directly touch the filesystem.
Every tool in the agent loop routes through ``PermissionManager``,
which validates, prompts, and then dispatches to ``FileSystemWrapper``.
"""

from __future__ import annotations

import re
import os
from pathlib import Path

from nanocode.permission.path_validator import PathValidator
from nanocode.permission.permission_store import PermissionStore
from nanocode.permission.permission_prompt import PermissionPrompt
from nanocode.permission.fs_wrapper import FileSystemWrapper

# Max shell command length (configurable via env)
MAX_COMMAND_LENGTH = int(os.environ.get("NANOCODE_MAX_CMD_LENGTH", "8192"))

# Patterns that suggest a shell command is referencing an external path.
# This is a best-effort heuristic, not a security boundary.
_TRAVERSAL_PATTERNS = re.compile(
    r'(?:^|\s)(?:'
    r'cat|ls|cd|rm|cp|mv|chmod|chown|mkdir|touch|head|tail|less|more|'
    r'nano|vim|vi|code|explorer|open|xdg-open|type|where|which|'
    r'Get-ChildItem|Get-Content|Set-Content|Remove-Item|Copy-Item|'
    r'Move-Item|Invoke-Expression'
    r')\s+'
    r'([a-zA-Z]:\\|\\\\|\.\.\\|/|\.\./)'
)

_SENSITIVE_REF_PATTERN = re.compile(
    r'(?:~[/\\])?(?:\.ssh|\.aws|\.gcp|\.config|\.kube|AppData|Application Data|'
    r'Users[/\\]\w+[/\\]|home[/\\]\w+[/\\])'
)

# Destructive command patterns blocked unconditionally.
_DESTRUCTIVE_PATTERNS = re.compile(
    r'(?:^|\s)(?:'
    r'rm\s+-[rfRF]{1,2}\s+[/\\]|'              # rm -rf /  (any flag combo)
    r'dd\s+if=|'                               # dd if=/dev/sda
    r'>\s*/dev/sd|'                            # redirect to block device
    r'mkfs\.|'                                 # format filesystem
    r':\(\)\s*\{|'                             # fork bomb
    r'chmod\s+-R\s+0{4}\s+/|'                  # chmod -R 0000 /
    r'(?:wget|curl)\s+.*\s*\||'                # fetch and pipe to shell
    r'bash\s+<(?:curl|wget)|'                   # fetch and exec
    r'sh\s+-c\s+"\s*rm\s+-[rfRF]{1,2}'         # sh -c "rm -rf"  
    r')\s*'
)


class PermissionManager:
    """Permission-enforcing filesystem facade.

    Usage::

        pm = PermissionManager(Path.cwd())
        content = pm.read("/some/path", "reading the config")
        pm.write("/other/path", "content", "writing output")
        files = pm.glob("**/*.py", ".")
    """

    def __init__(self, workspace_root: Path):
        self._workspace_root = workspace_root.resolve()
        self._validator = PathValidator(self._workspace_root)
        self._store = PermissionStore(self._workspace_root)
        self._fs = FileSystemWrapper()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def workspace_root(self) -> Path:
        return self._workspace_root

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    def read_text(
        self,
        path: str,
        reason: str = "",
        offset: int = 0,
        limit: int | None = None,
    ) -> str:
        """Read text from *path*. Returns the file content."""
        resolved = self._authorize(path, "read", reason)
        lines = self._fs.read_lines(resolved, offset, limit)
        context = "".join(f"{offset + idx + 1:4}| {line}" for idx, line in enumerate(lines))
        return context

    def write_text(self, path: str, content: str, reason: str = "") -> None:
        """Write *content* to *path*."""
        resolved = self._authorize(path, "write", reason)
        self._fs.write_text(resolved, content)

    def edit_text(
        self,
        path: str,
        old: str,
        new: str,
        all_occurrences: bool = False,
        reason: str = "",
    ) -> str:
        """Replace *old* with *new* in *path*.

        Returns ``"ok"`` on success or an error message string.
        """
        resolved = self._authorize(path, "edit", reason)

        if not self._fs.exists(resolved):
            return "error: file not found"

        text = self._fs.read_text(resolved)

        if old not in text:
            return "error: old_string not found"

        count = text.count(old)
        if not all_occurrences and count > 1:
            return f"error: old_string appears {count} times, must be unique (use all=true)"

        success = self._fs.replace_text(resolved, old, new, all_occurrences)
        return "ok" if success else "error: replacement failed"

    def delete(self, path: str, reason: str = "") -> None:
        """Delete a file or directory at *path*."""
        resolved = self._authorize(path, "delete", reason)
        self._fs.delete(resolved)

    # ------------------------------------------------------------------
    # Glob / search
    # ------------------------------------------------------------------

    def glob(self, pattern: str, root: str = ".", reason: str = "") -> str:
        """Find files matching *pattern* under *root*.

        Returns newline-separated paths or ``"none"``.
        """
        # The root must be inside the workspace
        resolved_root = self._resolve(root)
        if not self._validator.is_inside_workspace(resolved_root):
            raise PermissionError(
                f"Glob root {resolved_root} is outside the workspace. "
                f"Use the permission prompt to approve it."
            )
        files = self._fs.glob(pattern, resolved_root)
        return "\n".join(str(f) for f in files) or "none"

    def grep(self, pattern: str, root: str = ".", reason: str = "") -> str:
        """Search files under *root* for regex *pattern*.

        Returns newline-separated hits or ``"none"``.
        """
        resolved_root = self._resolve(root)
        if not self._validator.is_inside_workspace(resolved_root):
            raise PermissionError(
                f"Grep root {resolved_root} is outside the workspace."
            )
        compiled = re.compile(pattern)
        hits = self._fs.grep(compiled, resolved_root)
        return "\n".join(hits) or "none"

    # ------------------------------------------------------------------
    # Shell
    # ------------------------------------------------------------------

    def run_command(self, command: str, reason: str = "", line_callback=None) -> str:
        """Run a shell command. The working directory is always the workspace.

        If *line_callback* is provided, it is called with each line of output
        as it arrives (for live streaming in the CLI).

        If the command references a path outside the workspace (heuristic),
        the user is prompted for permission.
        """
        # Enforce max command length
        if len(command) > MAX_COMMAND_LENGTH:
            return f"(denied: command exceeds {MAX_COMMAND_LENGTH} character limit)"

        # Block destructive patterns unconditionally
        if _DESTRUCTIVE_PATTERNS.search(command):
            return "(denied: command matches a destructive pattern and was blocked)"

        # Best-effort check for external path references
        if _TRAVERSAL_PATTERNS.search(command) or _SENSITIVE_REF_PATTERN.search(command):
            decision = self._prompt_external_command(command, reason)
            if decision == PermissionPrompt.DENY:
                return "(denied: command references paths outside the workspace)"

        return self._fs.run_command(command, self._workspace_root, line_callback=line_callback)

    # ------------------------------------------------------------------
    # Authorization internals
    # ------------------------------------------------------------------

    def _resolve(self, path: str) -> Path:
        """Resolve *path* to canonical form.  Raises ``PermissionError`` on
        obvious traversal."""
        resolved = self._validator.resolve(path)
        return resolved

    def _authorize(self, path: str, operation: str, reason: str) -> Path:
        """Resolve *path*, check containment, prompt if needed.

        Returns the resolved canonical ``Path``.

        Raises ``PermissionError`` if the user denies access.
        """
        resolved = self._resolve(path)

        # Check: inside workspace?
        check = self._validator.check_access(resolved)

        if check["allowed"]:
            # Inside workspace and not sensitive — allow
            return resolved

        # Check if previously allowed
        if self._store.is_path_allowed(resolved):
            return resolved

        if check["sensitive"]:
            if self._store.is_sensitive_allowed(resolved):
                return resolved
            decision = PermissionPrompt.confirm_sensitive(
                resolved, operation, reason
            )
        else:
            decision = PermissionPrompt.confirm_outside(
                resolved, operation, reason
            )

        if decision == PermissionPrompt.ALLOW_ONCE:
            if check["sensitive"]:
                self._store.add_sensitive_allowed(resolved)
            return resolved

        if decision == PermissionPrompt.ALWAYS_ALLOW:
            self._store.add_always_allowed(resolved)
            return resolved

        raise PermissionError(
            f"Permission denied: {operation} on {resolved}"
        )

    def _prompt_external_command(self, command: str, reason: str) -> str:
        """Prompt user about a shell command that may access external paths."""
        print()
        print("\033[2m╭─ \033[1m\033[33mShell Command — External Path Reference\033[0m\033[2m ─────────────────────────────────╮\033[0m")
        print("\033[2m│\033[0m")
        print("\033[2m│\033[0m  This command may reference paths outside the workspace:")
        print("\033[2m│\033[0m")
        print(f"\033[2m│\033[0m  \033[36m{command[:70]}\033[0m")
        if reason:
            print(f"\033[2m│\033[0m  \033[33mReason:\033[0m {reason}")
        print("\033[2m│\033[0m")
        print("\033[2m├────────────────────────────────────────────────────────────────────┤\033[0m")
        print("\033[2m│\033[0m")
        print("\033[2m│\033[0m  \033[32m[1]\033[0m Allow Once")
        print("\033[2m│\033[0m  \033[31m[2]\033[0m Deny")
        print("\033[2m│\033[0m")

        while True:
            try:
                choice = input("\033[2m│\033[0m  \033[1m> \033[0m").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print()
                return PermissionPrompt.DENY

            if choice in ("1", "allow", "a"):
                return PermissionPrompt.ALLOW_ONCE
            if choice in ("2", "deny", "d", "n"):
                return PermissionPrompt.DENY
            print("\033[2m│\033[0m  \033[31mInvalid choice.\033[0m")


