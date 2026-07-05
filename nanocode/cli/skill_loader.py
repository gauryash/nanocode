"""Dynamic skill discovery from a flat ``skills/`` directory.

Scans ``.md`` files, parses YAML frontmatter, and produces the dicts
that ``config.py`` previously hardcoded (``AGENT_FILES``, ``AGENT_TOOLS``).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from nanocode.cli.frontmatter import parse_frontmatter

__all__ = [
    "SkillMeta",
    "discover_skills",
    "build_skill_config",
    "resolve_skill_path",
    "NATIVE_TOOLS",
]

# Nanocode's internal tool set (including stub tools from tools.py)
NATIVE_TOOLS: Set[str] = {"read", "write", "edit", "glob", "grep", "bash", "intercom", "contact_supervisor", "webfetch"}

# External tool names that map to nanocode tools
_TOOL_ALIASES: Dict[str, str] = {
    "find": "glob",
    "web_search": "webfetch",
    "fetch_content": "webfetch",
}

# Tools that are just shell commands (available via bash) — silently dropped
_DROPPED_TOOLS: Set[str] = {"ls"}


class SkillMeta:
    """Parsed metadata for a single skill file."""

    __slots__ = ("name", "description", "filename", "tools", "raw_metadata")

    def __init__(
        self,
        name: str,
        description: str,
        filename: str,
        tools: Set[str],
        raw_metadata: Dict[str, str],
    ) -> None:
        self.name = name
        self.description = description
        self.filename = filename
        self.tools = tools
        self.raw_metadata = raw_metadata


def _normalise_tools(raw: Optional[str]) -> Set[str]:
    """Parse a comma-separated tool string into a set of nanocode tool names."""
    if not raw:
        return set()

    result: Set[str] = set()
    for token in raw.split(","):
        name = token.strip()
        if not name:
            continue

        name = _TOOL_ALIASES.get(name, name)
        if name in _DROPPED_TOOLS:
            continue
        result.add(name)
    return result


def discover_skills(skills_dir: str) -> List[SkillMeta]:
    """Scan *skills_dir* and return metadata for every ``.md`` file.

    Files without frontmatter are included with an empty tool set.
    The skill name comes from the ``name`` field in frontmatter, or
    from the filename (stem) if no ``name`` is set.
    """
    skills: List[SkillMeta] = []
    root = Path(skills_dir)

    if not root.is_dir():
        return skills

    for entry in sorted(root.iterdir()):
        if entry.suffix.lower() != ".md":
            continue

        content = entry.read_text(encoding="utf-8")
        meta, _ = parse_frontmatter(content)

        name = meta.get("name", entry.stem)
        description = meta.get("description", "")
        tools = _normalise_tools(meta.get("tools"))
        raw_meta = {k: v for k, v in meta.items() if k not in ("name", "description", "tools")}

        skills.append(SkillMeta(
            name=name,
            description=description,
            filename=entry.name,
            tools=tools,
            raw_metadata=raw_meta,
        ))

    return skills


def _dedup_name(s: SkillMeta, used: Set[str]) -> str:
    """Resolve a unique key for *s*, handling frontmatter name collisions."""
    name = s.name
    if name not in used:
        return name
    name = Path(s.filename).stem
    if name not in used:
        return name
    n = 2
    while f"{name}-{n}" in used:
        n += 1
    return f"{name}-{n}"


def build_skill_config(skills: List[SkillMeta]) -> Tuple[Dict[str, str], Dict[str, Set[str]]]:
    """Build ``(agent_files, agent_tools)`` with consistent name deduplication.

    *agent_files* maps skill name → filename.
    *agent_tools* maps skill name → set of allowed nanocode tool names.
    Skills with an empty ``tools`` field get the full native tool set.
    """
    agent_files: Dict[str, str] = {}
    agent_tools: Dict[str, Set[str]] = {}
    used: Set[str] = set()

    # Process skills where frontmatter name matches filename stem first
    # (these are the "primary" files). Renamed files get fallback names.
    ranked = sorted(skills, key=lambda s: (s.name != Path(s.filename).stem, s.filename))

    for s in ranked:
        key = _dedup_name(s, used)
        used.add(key)
        agent_files[key] = s.filename
        if s.tools:
            agent_tools[key] = s.tools & NATIVE_TOOLS
        else:
            agent_tools[key] = set(NATIVE_TOOLS)

    return agent_files, agent_tools


def resolve_skill_path(skills_dir: str, filename: str) -> str:
    """Resolve a skill filename to an absolute path."""
    return str(Path(skills_dir).resolve() / filename)
