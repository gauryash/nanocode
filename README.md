# nanocode

Minimal coding agent. Zero dependencies. Uses the [OpenCode Go](https://opencode.ai) API.

244 built-in skills, auto-classified from your prompt. Run from **any directory**.

![screenshot](screenshot.png)

## Features

- Full agentic loop with tool use (auto-iterates until no more tool calls)
- Tools: `read`, `write`, `edit`, `glob`, `grep`, `bash`
- **244 built-in skills** — auto-discovered from `agent-skills.md` catalog
- **Skill auto-classification** — LLM matches your prompt to the best skill (or use `/use <skill>`)
- **Two modes**: `plan` (think, research, design) and `build` (implement, write code)
- Per-skill conversation memory — switching skills preserves context for each
- Conversation history with `/c` to clear
- Colored terminal output
- Switch models in-session with `/model`
- Sessions auto-saved and restorable by ID prefix

## Setup

### Dev (run from source, no install)

```bash
git clone <repo> && cd nanocode
cp .env.example .env          # then edit .env with your API key
python -m nanocode
```

`.env` is auto-loaded from CWD. Env vars take precedence.

### Prod (global install)

Skills are bundled into the package — install once, run anywhere:

```bash
git clone <repo> && cd nanocode
pip install .
```

Then set your key permanently:

```bash
# Linux / macOS — add to ~/.bashrc or ~/.zshrc
export OPENCODE_GO_API_KEY="your-key"

# Windows cmd (restart terminal after)
setx OPENCODE_GO_API_KEY "your-key"

# Windows PowerShell
[Environment]::SetEnvironmentVariable("OPENCODE_GO_API_KEY", "your-key", "User")
```

Now run from **any directory**:

```bash
nanocode
```

> Accepts `OPENCODE_GO_API_KEY` or `OPENCODE_API_KEY`. Optional: `MODEL`, `MAX_TOKENS`, `SKILLS_DIR`.

### Re-install (clean)

```bash
pip uninstall nanocode-go -y && pip install .
```

## Commands

| Command | Description |
|---|---|
| `/c` | Clear conversation |
| `/q`, `exit` | Quit |
| `/skills` | List all 244 available skills with descriptions |
| `/skill` | Show current skill |
| `/skill <id\|num>` | Manually switch skill (e.g. `/skill debugger` or `/skill 42`) |
| `/use <skill>` | Same as `/skill` — activate a named skill |
| `/plan` | Switch to plan mode (analysis, design, research) |
| `/build` | Switch to build mode (implementation, coding) |
| `/models` | Fetch and list available OpenCode Go models |
| `/model` | Show current model |
| `/model <id\|num>` | Switch model — clears conversation |
| `/sessions` | List saved sessions |
| `/session` | Show current session ID |
| `/session new` | Save and start a new session |
| `/session <id>` | Restore a session by ID prefix |
| `/help` | Show help, current model, and current skill |

## Skills

nanocode ships with **244 skills** discovered from the `agent-skills.md` catalog. Each skill has a name and description. Skills are organized under `nanocode/skills/` in subdirectories, with command and agent files.

On every message, nanocode classifies your prompt against the skill catalog:

- **Confidence ≥ 0.8** — auto-switches to the matched skill
- **0.4–0.7** — shows a hint with the `/use` command to activate it
- **< 0.4** — no skill active

Override anytime: `/skill architect`, `/skill debugging-toolkit`, `/skill 14`.

The root `skills/` directory at your project CWD takes priority over bundled skills — useful for custom skill development.

### Customizing skills

To add a new skill, create a directory under `skills/<skill-name>/` with a `SKILL.md` file, then add an entry to `skills/agent-skills.md`. Point `SKILLS_DIR` at a different folder to use your own skill library:

```bash
export SKILLS_DIR="/home/me/my-skills"
```

## System prompt

nanocode supports a two-tier prompt system:

- **`nanocode/system.md`** — base system prompt (shared across all skills)
- **Skill-specific prompts** — loaded from skill files per skill

The two are combined at runtime: system prompt first, then skill prompt.

Customize with the `SYSTEM_PROMPT_PATH` environment variable:

```bash
export SYSTEM_PROMPT_PATH="/home/me/custom-system.md"
```

## Tools

| Tool | Description |
|---|---|
| `read` | Read file with line numbers, offset/limit |
| `write` | Write content to file |
| `edit` | Replace string in file (must be unique unless `all=true`) |
| `glob` | Find files by pattern, sorted by mtime |
| `grep` | Search files for regex |
| `bash` | Run shell command (30s timeout) |

## Sessions

Conversations are auto-saved to `.nanocode/sessions/` after each turn. Each session gets a random 10-character hex ID.

- Auto-save on every turn, `/c`, `/session new`, restore, and quit
- Restore any saved session with `/session <prefix>` — just the first few hex chars is enough
- Start fresh without losing history with `/session new`

## Example

```
nanocode-go · deepseek-v4-flash (openai) · build · no-skill · /home/user/project
  session a1b2c3   244 skills available · /skills to list

──────────────────────────────────────
> what files are here?
──────────────────────────────────────

> glob(**/*.py)
  `- nanocode.py

> There's one Python file: nanocode.py
```

## Pre-commit secret scanning

A pre-commit hook is provided to scan staged changes for accidentally committed secrets:

```bash
git config core.hooksPath .githooks
```

To scan manually at any time:

```bash
python scripts/scan-secrets.py        # staged changes only
python scripts/scan-secrets.py --all  # entire repository
```

## License

MIT
