# Gemini CLI (`gemini -p`) — Capability Reference

*Self-reported on 2026-02-16, verified against gemini CLI on macOS.*

---

## 1. Available Tools

| Tool | What it does | Key Params | Limits |
|------|-------------|------------|--------|
| `list_directory` | Lists files and subdirectories | `dir_path`, `ignore` (glob array), `file_filtering_options` | May truncate on very large directories |
| `read_file` | Reads file content | `file_path`, `offset` (line), `limit` (lines) | Large files truncated; use `offset`+`limit` to paginate. Supports text, images, audio, PDF |
| `grep_search` | Regex pattern search in files | `pattern`, `dir_path`, `include` (glob), `before/after/context`, `case_sensitive` | Returns max 100 matches |
| `glob` | Find files matching glob patterns | `pattern`, `dir_path`, `case_sensitive`, `respect_git_ignore` | File discovery only, not content search |
| `run_shell_command` | Execute shell command | `command`, `working_dir` | No interactive commands (vim, ssh, etc.); long-running commands block unless backgrounded with `&` |
| `google_web_search` | Web search via Google Search | `query` | Number and content of results determined by API |
| `ask_user` | Prompt user for information | `questions` (array: multiple-choice, free-text, yes/no) | Cannot proceed until response received; useless in `-p` mode |
| `write_todos` | Manage task plan/checklist | `todos` array with description + status | Planning/tracking only, not execution |
| `save_memory` | Persist a fact across sessions | `fact` (string) | For short user preferences; not large data |
| `activate_skill` | Activate a named skill | `name` (e.g. `skill-creator`) | Only available skills can be used |
| `codebase_investigator` | Deep codebase analysis sub-agent | `objective` (detailed description) | Best for high-level understanding; not small targeted changes |
| `cli_help` | Answer questions about Gemini CLI | `question` | Meta-tool |

**Note on file writing:** `write_file` and `replace` tools exist but require the session to have them enabled. If not present, Gemini cannot directly write files — must use `run_shell_command` to write via shell (`cat`, `tee`, etc.).

---

## 2. Agentic / Autonomous Capabilities

- **Multi-step workflows:** Built on a "plan-execute" cycle managed through `write_todos`
  1. Break task into subtasks with `write_todos`
  2. Execute each, updating status (`in_progress` → `completed`)
  3. Loop: run tests → read output → identify error → fix → re-run

- **Parallel tool calls:** Multiple independent tool calls in a single turn execute in parallel (e.g., `glob` for `.py` and `.js` simultaneously)

- **Sub-agent tools:**
  - `codebase_investigator` — spawns a specialized analysis sub-agent
  - `cli_help` — spawns a CLI documentation sub-agent

- **Self-correction:** Parses error output from failed tool calls and adjusts approach in next turn

- **No true parallel worker spawning** — sub-agents are specialized single-purpose tools, not general parallel forks

---

## 3. File System Operations

- **Default working directory:** Directory where `gemini` CLI was launched
- **File reading:** `read_file` with `offset`/`limit` pagination for large files. Supports text, images, audio, PDFs
- **Large context window:** Gemini can hold multiple large files in context simultaneously
- **`--include-directories` flag:** Provides Gemini with broader project structure context from startup (not a tool behavior change — just initial context injection)
- **`write_file` / `replace`:** Available when session is configured for it; otherwise use `run_shell_command` to write
- **`.geminiignore`:** Gemini respects `.geminiignore` files (similar to `.gitignore`) when listing/reading directories

---

## 4. Shell / Bash Execution

- **Allowed:** Any non-interactive command in user's PATH — compilers, build tools, git, file manipulation, etc.
- **Cannot run:** Interactive commands (`vim`, `ssh`, password prompts, interactive REPLs)
- **Long-running commands** must be backgrounded with `&` or they block Gemini's operation
- **Non-sandbox mode (default):** Direct host execution with user-level permissions
  - Before destructive commands, Gemini explains what it will do (subject to approval mode)
- **`--sandbox` mode:** Executes inside a restricted environment (Docker-like) with limited FS and network access

---

## 5. Context Window & Memory

- **Context window:** Very large (Gemini 2.5 Pro: up to 1M tokens). Exact session limit not exposed via CLI flag
- **Large codebase strategy:** Uses `glob`/`grep_search` to identify relevant files, then `read_file` on that subset — does NOT load entire codebase at once
- **`--resume` flag:** Reloads conversation history from a previous session. Provides prior interaction context
- **`save_memory` tool:** Stores user-specific facts permanently for all future sessions (e.g., "always use tabs for indentation")
- **In-session context:** All tool results and conversation history accumulate within the session

---

## 6. Approval Modes

| Mode | Behavior |
|------|---------|
| `default` (unspecified) | Prompted to approve each tool call or group of parallel calls |
| `auto_edit` | Auto-approves file edit tools; still prompts for `run_shell_command` |
| `plan` | Presents high-level plan first; approves all plan-related tool calls once plan is confirmed |
| `yolo` | Auto-approves **all** tool calls — fastest but most dangerous. Use with extreme caution |

```bash
# Fully autonomous (no prompts)
gemini --approval-mode yolo -p "your prompt"

# Auto-approve file edits only
gemini --approval-mode auto_edit -p "your prompt"
```

---

## 7. Web & External Access

- **Google Web Search:** Yes — via `google_web_search` tool (explicit Google integration)
- **No other external service access** unless a specific tool is provided for it
- Cannot access arbitrary APIs or browse websites without the web tools

---

## 8. What Gemini Cannot Do

| Limitation | Notes |
|-----------|-------|
| No visual perception | Cannot see screen or interact with GUIs |
| No interactive commands | `vim`, `ssh`, password prompts block execution |
| No parallel worker spawning | `codebase_investigator` is specialized, not general parallel fork |
| `ask_user` is useless in `-p` mode | Cannot pause for user input mid-run |
| `write_file`/`replace` may be absent | Session-config dependent; use `run_shell_command` as fallback |
| Knowledge cutoff | Training data limited; use `google_web_search` for post-cutoff info |
| `--all-files` flag does NOT exist | Despite being in some documentation; confirmed rejected by CLI |

### Common Failure Modes in `-p` Mode

| Failure | Cause | Fix |
|---------|-------|-----|
| Task requires unknown info | No `ask_user` available | Provide all info upfront in the prompt |
| Command hangs | Interactive input required | Background with `&` or avoid interactive commands |
| Ambiguous goal | Vague prompt → lots of clarification attempts | Be explicit and self-contained in prompts |
| File write fails | `write_file` not in session tools | Use `run_shell_command` with `tee` or `cat` |

---

## 9. Best Practices for Max Performance

### Leverage the Large Context Window
Don't be shy about giving Gemini context upfront:
```bash
gemini -p "Refactor the User class from file1 to use Database from file2" \
  --include-directories src/
```

### For `-p` (Headless) Mode
- Assume Gemini has amnesia — provide **everything** in the prompt
- State explicitly: every file to read, every command to run, the exact goal
- One complete, self-contained instruction

### For Complex Code Tasks
```
"First, create a plan to add a /users endpoint to the Express app.
Then, implement the route in routes/users.js,
the controller in controllers/users.js,
and add a unit test in tests/users.test.js."
```

### Skills System
For recurring complex tasks, use `skill-creator` to teach Gemini a named multi-step workflow. Then `activate_skill` triggers it reliably in future sessions.

### Output Format for Automation
```bash
gemini --output-format stream-json -p "..."   # Real-time JSON stream for UIs
gemini --output-format json -p "..."          # Single JSON result for parsing
```

---

## 10. CLI Flags & Options

```bash
# Core flags
-p, --prompt <text>              Non-interactive (headless) mode with prompt
-m, --model <model>              Override model
-d, --debug                      Debug mode (open debug console with F12)
-s, --sandbox                    Run in sandbox mode
-y, --yolo                       Auto-accept all actions (alias for --approval-mode yolo)
    --approval-mode <mode>       default | auto_edit | yolo | plan
-r, --resume <latest|N>          Resume previous session (latest or index number)
    --list-sessions              List available sessions and exit
    --delete-session <N>         Delete session by index
    --include-directories <...>  Additional directories for workspace context (comma-sep or repeated)
    --allowed-tools <...>        Restrict to specific tools (array)
    --allowed-mcp-server-names   Allowed MCP server names (array)
    --experimental-acp           Start in ACP mode
    --output-format <format>     text | json | stream-json
    --raw-output                 Disable sanitization of model output (ANSI escape sequences)
    --accept-raw-output-risk     Suppress security warning for --raw-output
    --screen-reader              Enable screen reader accessibility mode
-e, --extensions <...>           Specify extensions to use (default: all)
-l, --list-extensions            List all available extensions and exit
-v, --version                    Show version
-h, --help                       Show help
```

### Output Format Options

| Format | Description | Best for |
|--------|-------------|---------|
| `text` | Default human-readable | Terminal, piping |
| `json` | Single JSON object | Programmatic result parsing |
| `stream-json` | Stream of JSON objects (thoughts, tool calls, final answer) | UIs, real-time processing |

### MCP Integration

```bash
gemini --allowed-mcp-server-names server1,server2 -p "..."
```

MCP servers provide additional tools. Use `gemini mcp` subcommands to manage servers.

---

## Key Architectural Insight

Gemini's biggest strength for this multi-agent system is its **massive context window** (up to 1M tokens). This makes it ideal for:
- Reading entire codebases at once for holistic review
- Holding all prior reviews, critiques, and code simultaneously
- Long-horizon planning tasks without truncation risk

Its `google_web_search` tool gives it unique access to real-time web information — useful for checking current library versions, recent CVEs, or up-to-date best practices during code review.

The Critic role is well-suited to Gemini because it can hold the entire history (code + all reviews + all prior critiques) in context with room to spare.
