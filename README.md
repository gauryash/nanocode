# nanocode

Minimal coding agent. Single Python file, zero dependencies, ~500 lines. Uses the [OpenCode Go](https://opencode.ai) API.

![screenshot](screenshot.png)

## Features

- Full agentic loop with tool use (auto-iterates until no more tool calls)
- Tools: `read`, `write`, `edit`, `glob`, `grep`, `bash`
- Conversation history with `/c` to clear
- Colored terminal output
- Auto-detects OpenAI vs Anthropic API style based on model family
- Switch models in-session with `/model`

## Setup

### 1. Create a `.env` file from the example

```bash
cp .env.example .env
```

Then edit `.env` and replace `your-key` with your real API key from https://opencode.ai.

> The script accepts either `OPENCODE_GO_API_KEY` **or** `OPENCODE_API_KEY`.

### 2. Load it and run

**Linux / macOS / Git Bash (Windows):**

```bash
set -a && source .env && set +a
python nanocode.py
```

**Windows Command Prompt (cmd):**

```cmd
for /f "tokens=*" %i in (.env) do set %i
python nanocode.py
```

**Windows PowerShell:**

```powershell
Get-Content .env | ForEach-Object { if ($_ -match '^([^#].+?)=(.+)$') { [Environment]::SetEnvironmentVariable($matches[1], $matches[2]) } }
python nanocode.py
```

### Or just export/set directly

**Linux / macOS / Git Bash:**

```bash
export OPENCODE_GO_API_KEY="your-key"
export MODEL="deepseek-v4-flash"
export MAX_TOKENS="8192"
python nanocode.py
```

**Windows cmd:**

```cmd
set OPENCODE_GO_API_KEY=your-key
set MODEL=deepseek-v4-flash
set MAX_TOKENS=8192
python nanocode.py
```

**Windows PowerShell:**

```powershell
$env:OPENCODE_GO_API_KEY="your-key"
$env:MODEL="deepseek-v4-flash"
$env:MAX_TOKENS="8192"
python nanocode.py
```

## Commands

| Command | Description |
|---|---|
| `/c` | Clear conversation history |
| `/q`, `exit` | Quit |
| `/models` | Fetch and list available OpenCode Go models |
| `/model` | Show current model |
| `/model <id\|num>` | Switch model (e.g. `/model deepseek-v4-pro` or `/model 3`) — clears conversation |
| `/help` | Show help and current model |

## Tools

| Tool | Description |
|---|---|
| `read` | Read file with line numbers, offset/limit |
| `write` | Write content to file |
| `edit` | Replace string in file (must be unique unless `all=true`) |
| `glob` | Find files by pattern, sorted by mtime |
| `grep` | Search files for regex |
| `bash` | Run shell command (30s timeout) |

## Example

```
nanocode-go | deepseek-v4-flash (openai) | /home/user/project

──────────────────────────────────────
> what files are here?
──────────────────────────────────────

> glob(**/*.py)
  `- nanocode.py

> There's one Python file: nanocode.py
```

## License

MIT
