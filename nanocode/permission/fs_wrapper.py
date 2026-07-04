"""FileSystemWrapper — the ONLY code allowed to touch the real filesystem.

No code outside this module should call ``open()``, ``Path.read_text()``,
``os.remove()``, or similar filesystem APIs directly.  Everything goes
through this wrapper, which is in turn only called by ``PermissionManager``.
"""

from __future__ import annotations

import glob as globlib
import os
import re
import shutil
import subprocess
from pathlib import Path


class FileSystemWrapper:
    """Low-level filesystem operations.

    These methods perform the actual I/O.  They assume the caller
    (``PermissionManager``) has already validated and authorized the
    request.  No permission checking is performed here.
    """

    # ------------------------------------------------------------------
    # File operations
    # ------------------------------------------------------------------

    @staticmethod
    def read_text(path: Path, encoding: str = "utf-8") -> str:
        with open(str(path), "r", encoding=encoding, errors="replace") as f:
            return f.read()

    @staticmethod
    def write_text(path: Path, content: str, encoding: str = "utf-8") -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(str(path), "w", encoding=encoding) as f:
            f.write(content)

    @staticmethod
    def read_lines(path: Path, offset: int = 0, limit: int | None = None) -> list[str]:
        with open(str(path), "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()
        selected = lines[offset : offset + limit] if limit else lines[offset:]
        return selected

    @staticmethod
    def replace_text(
        path: Path,
        old: str,
        new: str,
        all_occurrences: bool = False,
    ) -> bool:
        """Replace *old* with *new* in *path*.  Returns True on success.

        Returns False if ``old`` was not found, or if ``old`` appears
        multiple times and ``all_occurrences`` is False.
        """
        with open(str(path), "r", encoding="utf-8", errors="replace") as f:
            text = f.read()

        if old not in text:
            return False

        count = text.count(old)
        if not all_occurrences and count > 1:
            return False  # ambiguous

        replacement = text.replace(old, new) if all_occurrences else text.replace(old, new, 1)

        # Atomic write via temp file + replace
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(str(tmp), "w", encoding="utf-8") as f:
            f.write(replacement)
        os.replace(str(tmp), str(path))
        return True

    @staticmethod
    def ensure_dir(path: Path) -> None:
        """Create directory and parents if they don't exist."""
        path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def delete(path: Path) -> None:
        if path.is_dir():
            shutil.rmtree(str(path))
        else:
            path.unlink()

    # ------------------------------------------------------------------
    # Glob / search
    # ------------------------------------------------------------------

    @staticmethod
    def glob(pattern: str, root: str | Path = ".") -> list[Path]:
        """Return files matching *pattern* under *root*.

        Returns paths sorted by modification time (newest first).
        Paths are resolved to canonical absolute form.
        """
        root_p = Path(root)
        full_pattern = str(root_p / pattern)
        files = globlib.glob(full_pattern, recursive=True)
        files = sorted(
            files,
            key=lambda f: os.path.getmtime(f) if os.path.isfile(f) else 0,
            reverse=True,
        )
        return [Path(f).resolve() for f in files]

    @staticmethod
    def grep(pattern: re.Pattern, root: str | Path = ".") -> list[str]:
        """Search files under *root* for *pattern*.

        Returns up to 50 hits as ``path:lineno:line`` strings.
        """
        hits: list[str] = []
        root_p = Path(root)
        max_hits = 50

        for filepath in globlib.glob(str(root_p / "**"), recursive=True):
            if not os.path.isfile(filepath):
                continue
            try:
                with open(filepath, "r", encoding="utf-8", errors="replace") as f:
                    for line_num, line in enumerate(f, 1):
                        if pattern.search(line):
                            hits.append(f"{filepath}:{line_num}:{line.rstrip()}")
                            if len(hits) >= max_hits:
                                return hits
            except Exception:
                pass
        return hits

    # ------------------------------------------------------------------
    # Shell
    # ------------------------------------------------------------------

    @staticmethod
    def run_command(
        command: str,
        cwd: Path,
        timeout: int = 30,
        line_callback=None,
    ) -> str:
        """Run a shell command with *cwd* as the working directory.

        If *line_callback* is provided, it is called with each line of
        output as it arrives (useful for live streaming in the CLI).

        Returns combined stdout+stderr.
        """
        proc = subprocess.Popen(
            command,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=str(cwd),
            text=True,
        )

        output_lines: list[str] = []
        try:
            while True:
                line = proc.stdout.readline()
                if not line and proc.poll() is not None:
                    break
                if line:
                    output_lines.append(line)
                    if line_callback:
                        line_callback(line.rstrip())
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            output_lines.append("\n(timed out after {}s)".format(timeout))

        return "".join(output_lines).strip() or "(empty)"

    # ------------------------------------------------------------------
    # Path info
    # ------------------------------------------------------------------

    @staticmethod
    def exists(path: Path) -> bool:
        return path.exists()

    @staticmethod
    def is_file(path: Path) -> bool:
        return path.is_file()

    @staticmethod
    def is_dir(path: Path) -> bool:
        return path.is_dir()
