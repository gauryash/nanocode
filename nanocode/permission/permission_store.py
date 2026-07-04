"""PermissionStore — persist allowed paths per workspace."""

from __future__ import annotations

import json
import os
from pathlib import Path


class PermissionStore:
    """Manages the permissions file for a workspace.

    The permissions file is stored at ``<workspace>/.nanocode/permissions.json``.
    It tracks:
      - The workspace root (for verification).
      - ``always_allowed`` paths that the user has granted permanent access to.
      - ``sensitive_allowed`` paths that are sensitive but user allowed once.
    """

    def __init__(self, workspace_root: Path):
        self._workspace_root = workspace_root.resolve()
        self._store_dir = self._workspace_root / ".nanocode"
        self._store_path = self._store_dir / "permissions.json"
        self._data = self._load()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_path_allowed(self, resolved: Path) -> bool:
        """Return True if *resolved* (a canonical absolute path) has been
        permanently allowed by the user."""
        path_str = str(resolved)
        return path_str in self._data.get("always_allowed", [])

    def is_sensitive_allowed(self, resolved: Path) -> bool:
        """Return True if a sensitive path was previously allowed once."""
        path_str = str(resolved)
        return path_str in self._data.get("sensitive_allowed", [])

    def add_always_allowed(self, resolved: Path) -> None:
        """Grant permanent access to *resolved*."""
        path_str = str(resolved)
        if path_str not in self._data["always_allowed"]:
            self._data["always_allowed"].append(path_str)
            self._save()

    def add_sensitive_allowed(self, resolved: Path) -> None:
        """Record that a sensitive path was allowed once (session scope)."""
        path_str = str(resolved)
        if path_str not in self._data["sensitive_allowed"]:
            self._data["sensitive_allowed"].append(path_str)
            self._save()

    def revoke_all(self) -> None:
        """Clear all stored permissions (except the workspace marker)."""
        self._data["always_allowed"] = []
        self._data["sensitive_allowed"] = []
        self._save()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _load(self) -> dict:
        default = {
            "version": 1,
            "workspace": str(self._workspace_root),
            "always_allowed": [],
            "sensitive_allowed": [],
        }
        if not self._store_path.exists():
            # Create store dir if needed
            self._store_dir.mkdir(parents=True, exist_ok=True)
            self._data = dict(default)
            self._save()
            return self._data

        try:
            with open(str(self._store_path), "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return dict(default)

        # Ensure all keys exist
        for key in default:
            data.setdefault(key, default[key])
        return data

    def _save(self) -> None:
        self._store_dir.mkdir(parents=True, exist_ok=True)
        tmp = self._store_path.with_suffix(".json.tmp")
        with open(str(tmp), "w", encoding="utf-8") as f:
            json.dump(self._data, f, indent=2, ensure_ascii=False)
        os.replace(str(tmp), str(self._store_path))
