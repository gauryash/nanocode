"""PermissionPrompt — interactive user dialogs for permission decisions."""

from __future__ import annotations

import sys
from pathlib import Path

# ANSI colors
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
GREEN = "\033[32m"
BOLD = "\033[1m"
DIM = "\033[2m"
RESET = "\033[0m"


class PermissionPrompt:
    """Displays permission prompts to the user and collects decisions.

    This is the interactive component that asks the user whether NanoCode
    should be allowed to read/write a path outside the workspace or access
    a sensitive file inside it.
    """

    # Decision constants
    ALLOW_ONCE = "allow_once"
    ALWAYS_ALLOW = "always_allow"
    DENY = "deny"

    @classmethod
    def confirm_outside(
        cls,
        path: Path,
        operation: str,
        reason: str = "",
    ) -> str:
        """Prompt user for permission to access a file *outside* the workspace.

        Returns one of ``ALLOW_ONCE``, ``ALWAYS_ALLOW``, or ``DENY``.
        """
        return cls._prompt(
            title="Outside Workspace Access",
            path=path,
            operation=operation,
            reason=reason,
            warning="This file is outside the NanoCode workspace.",
            show_always=True,
        )

    @classmethod
    def confirm_sensitive(
        cls,
        path: Path,
        operation: str,
        reason: str = "",
    ) -> str:
        """Prompt user for permission to access a *sensitive* file.

        Returns one of ``ALLOW_ONCE``, ``ALWAYS_ALLOW``, or ``DENY``.
        For sensitive files inside the workspace, we don't offer permanent
        "always allow" — only session-scoped allow-once.
        """
        return cls._prompt(
            title="Sensitive File",
            path=path,
            operation=operation,
            reason=reason,
            warning="This file contains sensitive information.",
            show_always=False,
        )

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @classmethod
    def _prompt(
        cls,
        *,
        title: str,
        path: Path,
        operation: str,
        reason: str,
        warning: str,
        show_always: bool,
    ) -> str:
        if not sys.stdout.isatty():
            # Non-interactive: deny by default
            return cls.DENY

        box_width = 72

        def hdr(t: str) -> str:
            inner = f"─ {t} "
            return f"{DIM}╭{inner}{DIM}{'─' * max(1, box_width - len(inner) - 2)}╮{RESET}"

        def v(text: str = "") -> str:
            return f"{DIM}│{RESET} {text}"

        def sep() -> str:
            return f"{DIM}├{'─' * max(1, box_width - 2)}┤{RESET}"

        def ftr() -> str:
            return f"{DIM}╰{'─' * max(1, box_width - 2)}╯{RESET}"

        print(f"\n{hdr(f'{BOLD}{RED}{title}{RESET}{DIM}')}")
        print(v())
        print(v(f"  {YELLOW}{warning}{RESET}"))
        print(v())
        print(v(f"  {BOLD}Path:{RESET}      {CYAN}{path}{RESET}"))
        print(v(f"  {BOLD}Operation:{RESET}  {operation}"))
        if reason:
            print(v(f"  {BOLD}Reason:{RESET}    {reason}"))
        print(v())
        print(sep())
        print(v())
        print(v("  Choose an option:"))
        print(v())
        print(v(f"  {GREEN}[1]{RESET} Allow Once"))
        if show_always:
            print(v(f"  {GREEN}[2]{RESET} Always Allow"))
            print(v(f"  {RED}[3]{RESET} Deny"))
        else:
            print(v(f"  {RED}[2]{RESET} Deny"))
        print(v())

        while True:
            try:
                choice = input(f"{DIM}│{RESET}  {BOLD}> {RESET}").strip().lower()
            except (EOFError, KeyboardInterrupt):
                print()
                return cls.DENY

            if choice in ("1", "allow", "allow once", "a"):
                return cls.ALLOW_ONCE
            if show_always and choice in ("2", "always", "always allow", "w"):
                return cls.ALWAYS_ALLOW
            if (show_always and choice in ("3", "deny", "d", "n")) or (not show_always and choice in ("2", "deny", "d", "n")):
                return cls.DENY
            # Invalid — loop
            print(f"{DIM}│{RESET}  {RED}Invalid choice.{RESET}")

        return cls.DENY  # unreachable
