"""Parse agent-skills.md catalog tables into {skill_name → description}.

The catalog at ``skills/agent-skills.md`` is the single source of truth for
skill metadata.  This module extracts name + description pairs from its
markdown tables so the LLM classifier can match user prompts to skills.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, Set

__all__ = [
    "SKILL_CATALOG",
    "load_catalog",
    "_parse_tables",
]

# Lines that indicate a table header row (we skip these)
_HEADER_RE = re.compile(r"^\|\s*skill\s*\|", re.IGNORECASE)
# Lines that are table separator rows (| --- | --- |)
_SEPARATOR_RE = re.compile(r"^\|[\s\-:]+\|")
# Table data row: | ... | ... |
_DATA_ROW_RE = re.compile(r"^\|(.+)\|(.+)\|$")


def _parse_tables(content: str) -> Dict[str, str]:
    """Extract ``{skill_name: description}`` from all markdown tables in *content*."""
    catalog: Dict[str, str] = {}
    seen: Set[str] = set()

    for line in content.split("\n"):
        line_stripped = line.strip()

        if not line_stripped.startswith("|"):
            continue
        if _HEADER_RE.match(line_stripped):
            continue
        if _SEPARATOR_RE.match(line_stripped):
            continue

        m = _DATA_ROW_RE.match(line_stripped)
        if not m:
            continue

        raw_name = m.group(1).strip()
        description = m.group(2).strip()

        name = raw_name.strip("*").strip()
        if not name or not description:
            continue
        if name in seen:
            continue
        seen.add(name)
        catalog[name] = description

    return catalog


def load_catalog(catalog_path: str | Path) -> Dict[str, str]:
    """Read and parse *catalog_path* (a markdown file with skill tables).

    Returns the ``{skill_name: description}`` dict.
    Raises ``FileNotFoundError`` if the file does not exist.
    """
    content = Path(catalog_path).read_text(encoding="utf-8")
    return _parse_tables(content)


# Lazy-loaded singleton — populated by ``config.py`` at import time.
SKILL_CATALOG: Dict[str, str] = {}
