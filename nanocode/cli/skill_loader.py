"""Skill file discovery + catalog-driven index.

Two sources:
  1. **Catalog** (``agent-skills.md``) — the single source of truth for
     skill names and descriptions (extracted via ``catalog.py``).
  2. **Recursive file scan** — finds every ``.md`` under ``skills/`` to
     build ``{skill_name → relative_path}``.

The catalog drives LLM classification; the file map loads the prompt.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from nanocode.cli.frontmatter import parse_frontmatter

__all__ = [
    "SkillMeta",
    "discover_skills",
    "discover_skill_files",
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

# Matches ``# Title`` at the start of a file
_H1_RE = re.compile(r"^#\s+(.+)$", re.MULTILINE)


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


def _name_from_h1(content: str) -> str | None:
    """Extract a hyphen-case name from the first ``# Title`` line."""
    m = _H1_RE.search(content)
    if not m:
        return None
    return m.group(1).strip().lower().replace(" ", "-")


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


def _potential_names(md_file: Path, content: str) -> list[str]:
    """Generate all plausible skill names for a file, most-specific first."""
    names: list[str] = []
    meta, _ = parse_frontmatter(content)

    fn = meta.get("name")
    if fn:
        names.append(fn)

    h1 = _name_from_h1(content)
    if h1 and h1 != fn:
        names.append(h1)

    if md_file.name.lower() == "skill.md":
        parent = md_file.parent.name
        if parent != fn and parent != h1:
            names.append(parent)

    stem = md_file.stem
    if stem != fn and stem != h1:
        names.append(stem)

    return names


def _is_skill_file(md_file: Path) -> bool:
    """Heuristic: is this ``.md`` file an actual skill (not a reference/README)?"""
    name_lower = md_file.name.lower()

    # Explicit non-skills
    if name_lower in ("readme.md", "index.md", "changelog.md", "summary.md"):
        return False

    parts_lower = [p.lower() for p in md_file.parts]

    # Files inside ``references/`` or ``resources/`` dirs are supporting docs
    if "references" in parts_lower or "resources" in parts_lower:
        return False

    # SKILL.md is always a skill
    if name_lower == "skill.md":
        return True

    # Files inside commands/ or agents/ directories
    parent_lower = md_file.parent.name.lower()
    if parent_lower in ("commands", "agents"):
        return True

    # Files directly inside a plugin directory (skills/<plugin>/<file>.md)
    # are potential skills iff they have frontmatter.
    # Check depth: should be at skills/<plugin>/<file>.md (3 parts from root)
    # or deeper in subdirs we haven't caught above
    if len(md_file.parts) >= 3:
        for i, p in enumerate(parts_lower):
            if p == "skills" and i + 2 < len(parts_lower):
                return True

    return False


def discover_skill_files(skills_dir: str) -> Dict[str, str]:
    """Recursively walk ``skills/`` and map ``{skill_name → relative_path}``.

    Only indexes files that look like real skills (not references/READMEs).
    Each file is indexed under **all** plausible names (frontmatter ``name``,
    H1-derived, parent directory for ``SKILL.md``, file stem).  The first
    file to claim a name wins.
    """
    mapping: Dict[str, str] = {}
    root = Path(skills_dir)

    if not root.is_dir():
        return mapping

    for md_file in sorted(root.rglob("*.md")):
        if not _is_skill_file(md_file):
            continue

        rel = md_file.relative_to(root)
        content = md_file.read_text(encoding="utf-8")

        for name in _potential_names(md_file, content):
            if name and name not in mapping:
                mapping[name] = str(rel.as_posix())

    return mapping


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
