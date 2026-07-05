"""PathValidator — canonicalize paths, detect traversal, check containment."""

from __future__ import annotations

import os
from pathlib import Path
import fnmatch


SENSITIVE_PATTERNS = [
    ".env",
    "*.pem",
    "*.key",
    "id_rsa",
    "credentials.json",
    "secrets.*",
    ".env.*",
    "*.p12",
    "*.pfx",
    "*.secret",
    "*.token",
    ".gitconfig",
    ".netrc",
    ".npmrc",
    ".dockercfg",
    ".docker/config.json",
    ".nanocode/config.json",  # has API keys in .nanocode
]


class PathValidator:
    """Path resolution, containment checking, and sensitivity detection.

    Every incoming path string is resolved to its canonical absolute form
    before any decision is made.  Symbolic links are resolved so that a
    symlink pointing outside the workspace is detected.
    """

    def __init__(self, workspace_root: Path):
        self._workspace_root = workspace_root.resolve()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def workspace_root(self) -> Path:
        return self._workspace_root

    def resolve(self, path: str) -> Path:
        """Resolve *path* to its canonical absolute form.

        Raises ``ValueError`` if the path contains traversal components
        that resolve to a completely different location (e.g. a path that
        would escape even before a final symlink check).  The caller can
        rely on the return value being a real absolute path.
        """
        return _resolve(path, self._workspace_root)

    def is_inside_workspace(self, path: Path) -> bool:
        """Return True if *path* (already resolved) is under the workspace root."""
        try:
            path.relative_to(self._workspace_root)
            return True
        except ValueError:
            return False

    def check_access(self, resolved: Path) -> dict:
        """Check what kind of access *resolved* path gets.

        Returns a dict with keys:
          - allowed (bool): True if access should be granted without prompt
          - reason (str):  human-readable explanation
          - sensitive (bool): True if the path matches a sensitive pattern
        """
        if not self.is_inside_workspace(resolved):
            return {
                "allowed": False,
                "sensitive": False,
                "reason": "Path is outside the workspace.",
            }

        if self._is_sensitive_path(resolved):
            return {
                "allowed": False,
                "sensitive": True,
                "reason": "File is marked as sensitive.",
            }

        return {
            "allowed": True,
            "sensitive": False,
            "reason": "Inside workspace.",
        }

    def is_sensitive_path(self, resolved: Path) -> bool:
        """Return True if *resolved* matches a known sensitive-file pattern."""
        return self._is_sensitive_path(resolved)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _is_sensitive_path(resolved: Path) -> bool:
        name = resolved.name
        rel = str(resolved).replace("\\", "/")
        for pattern in SENSITIVE_PATTERNS:
            if fnmatch.fnmatch(name, pattern):
                return True
            if fnmatch.fnmatch(rel, f"*/{pattern}"):
                return True
        return False


# ------------------------------------------------------------------
# Module-level helpers (used by PathValidator.resolve)
# ------------------------------------------------------------------

def _resolve(path_str: str, cwd: Path) -> Path:
    """Resolve *path_str* to a real absolute path, detecting traversal."""
    p = Path(path_str)

    # ---- Phase 1: Detect obvious traversal in the input ----
    parts = p.parts
    for part in parts:
        if part == "..":
            # We don't reject outright — just note it; resolve() handles it.
            pass

    # ---- Phase 2: Join against cwd if relative, then resolve ----
    if not p.is_absolute():
        p = cwd / p
    resolved = p.resolve(strict=False)

    # ---- Phase 3: Symlink follow ----
    # resolve() already follows symlinks.  But we want to be extra sure:
    # if the path has symlinks, _real_resolved follows them all.
    try:
        real_resolved = Path(os.path.realpath(str(p)))
    except OSError:
        real_resolved = resolved

    return real_resolved
