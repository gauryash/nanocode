"""Minimal YAML frontmatter parser for markdown skill files.

Expects ``---`` delimited blocks at the start of a file, with flat
``key: value`` pairs. No nested structures, no arrays, no indentation.
"""

from __future__ import annotations

import re
from typing import Dict, Tuple

__all__ = ["parse_frontmatter"]

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n?", re.DOTALL)
_LINE_RE = re.compile(r"^(\w[\w-]*?)\s*:\s*(.+?)\s*$")


def parse_frontmatter(content: str) -> Tuple[Dict[str, str], str]:
    """Parse YAML frontmatter from a markdown string.

    Returns ``(metadata, body)`` where *metadata* is a dict of key-value
    pairs and *body* is the markdown content after the frontmatter.

    If no frontmatter is found, returns ``({}, content)``.
    """
    m = _FRONTMATTER_RE.match(content)
    if not m:
        return {}, content

    raw = m.group(1)
    remaining = content[m.end():]

    data: Dict[str, str] = {}
    for line in raw.split("\n"):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        lm = _LINE_RE.match(line)
        if lm:
            data[lm.group(1)] = lm.group(2)

    return data, remaining
