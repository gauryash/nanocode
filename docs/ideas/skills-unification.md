# Skills Unification

## Problem Statement
How might we consolidate 22 orphaned prompt files across 3 directories into a single flat `skills/` directory, self-describing via YAML frontmatter, with a simplified two-mode CLI (`/plan` read-only, `/build` full access)?

## Recommended Direction
Merge all files into `skills/` (flat). Add a frontmatter parser that reads `tools:`, `systemPromptMode:`, `output:`, etc. to auto-configure tool permissions and behavior. The 6 native `agents/` files get minimal frontmatter added. `/plan` restricts to `{read, glob, grep}` and filters out skills that require write tools. `/build` has full `{read, write, edit, glob, grep, bash}`. `intercom` and `contact_supervisor` are stubbed as no-ops that return "not available."

## Key Assumptions to Validate
- [ ] The `reviewer.md` naming conflict is resolved (rename external one to `external-reviewer.md`)
- [ ] The 6 nanocode native files (coder, architect, etc.) are converted to frontmatter format without losing their prompt content
- [ ] `find` → `glob` and `ls` → `bash` mappings cover all tool references across external agents

## MVP Scope
1. Create `skills/` directory with all 22 files (rename conflicting `reviewer.md`)
2. Add YAML frontmatter to the 6 native agent files (minimal: `name`, `description`, `tools`)
3. Write `frontmatter.py` — minimal YAML parser for `---` delimited blocks
4. Write `skill_loader.py` — scans `skills/`, parses frontmatter, builds `AGENT_FILES` + `AGENT_TOOLS` dynamically
5. Stub `intercom` and `contact_supervisor` as no-ops
6. Update `config.py` to remove hardcoded `AGENT_FILES` and `AGENT_TOOLS`
7. Rewrite `/agent` → `/plan` and `/build` commands in the REPL loop

## Not Doing (and Why)
- **Multi-agent orchestration** — skills are prompt-only, no parallel execution or message passing. Stubs satisfy the YAML contract without the complexity.
- **PyYAML dependency** — frontmatter is simple enough for a ~20 line regex parser. One less dependency to maintain.
- **Subdirectory structure** — flat is simpler. Files with similar purposes use unique names.
- **Backward compatibility with `/agent`** — `/agent` is replaced by `/plan`/`/build`. The 6 old agents become skills you `/use` within a mode.
- **`inheritProjectContext`/`inheritSkills` fields** — irrelevant in a single-process CLI. Ignored.

## Open Questions
- Should `/plan` and `/build` automatically load a default skill (e.g., `/plan` loads `architect`, `/build` loads `coder`), or start with unskilled prompt and require `/use <skill>`?
