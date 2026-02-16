# Claude CLI (`claude -p`) — Capability Reference

*Self-reported on 2026-02-16, verified against claude-sonnet-4-5-20250929.*

---

## 1. Available Tools

### Core Tools (available in `-p` mode)

| Tool | Purpose | Key Limits |
|------|---------|------------|
| **Read** | Read file contents | 2000 lines default; truncates lines >2000 chars; supports PDF (max 20 pages), images, `.ipynb` |
| **Write** | Create/overwrite files | Must Read first if file exists; absolute paths only |
| **Edit** | Exact string replacement | Fails if `old_string` not unique; use `replace_all` for multi |
| **Glob** | File pattern matching | Returns paths sorted by modification time |
| **Grep** | Regex content search (ripgrep) | Modes: `content`, `files_with_matches`, `count`; supports `-A/-B/-C`, multiline |
| **Bash** | Execute shell commands | 2-min default timeout (max 10 min); shell state does NOT persist between calls |
| **Task** | Spawn sub-agents | Parallel or background; see §2 |
| **TodoWrite** | Structured task list | In-memory only; does not persist across sessions |
| **WebFetch** | Fetch and process a URL | Fails for authenticated URLs; HTML→markdown; 15-min cache |
| **WebSearch** | Web search | US only; structured results with domain filtering |
| **NotebookEdit** | Edit Jupyter notebook cells | Supports replace/insert/delete modes |
| **AskUserQuestion** | Prompt user for input | Useless in `-p` mode — no human to respond mid-run |
| **TaskOutput** | Get output from background Task | Pairs with `run_in_background: true` |
| **TaskStop** | Stop a background Task | — |

### Unlocking Tools with `--allowedTools`

By default in `-p` mode all tools are available. `--allowedTools` is a **whitelist** — restricts Claude to only those tools. Use it to sandbox sub-agents:

```bash
# Read-only analysis agent
claude -p "analyze..." --allowedTools "Read,Glob,Grep"

# Code writing agent
claude -p "implement..." --allowedTools "Read,Write,Edit,Bash"

# Full autonomous coding agent
claude -p "build..." --allowedTools "Bash,Write,Read,Edit,Glob,Grep,Task"
```

### MCP Tools (session-dependent)

Injected by MCP servers configured via `--mcp-config`. Examples: Figma, HuggingFace, Excalidraw. Not available in plain `-p` unless the MCP server is configured.

---

## 2. Agentic / Autonomous Capabilities

### Task Tool — Sub-agent Spawning

Spawns independent subprocess agents. Each has its own context window (no shared memory with parent).

**Available sub-agent types:**

| Type | Tools | Best for |
|------|-------|---------|
| `Bash` | Bash only | Git, shell ops, command execution |
| `general-purpose` | All tools | Complex multi-step research + coding |
| `Explore` | All except Task, Edit, Write | Codebase exploration, search — fast |
| `Plan` | All except Task, Edit, Write | Architecture design, planning |
| `claude-code-guide` | Glob, Grep, Read, WebFetch, WebSearch | Documentation questions |

**Parallelism:**
- Multiple Task calls in a single response execute **in parallel**
- `run_in_background: true` returns immediately with `task_id` + `output_file`
- Use `TaskOutput` or `Read` on output file to retrieve results
- Agents can be resumed with the returned agent ID via `resume` parameter
- 3–8 concurrent agents is a safe range; beyond that, watch resource pressure

**Communication:** Sub-agents return a single message to the parent. No sibling communication.

### Multi-step Workflow

Claude loops within a single `-p` invocation using agentic turns. Runs until:
1. Task is complete
2. `--max-turns` limit hit
3. Context window exhausted

Self-corrects by reading error output from Bash/tool failures and adjusting.

---

## 3. File System Operations

- **Read:** Any absolute path the OS user can access — no sandboxing
- **Write/Edit:** Requires read-first enforcement (enforced by system prompt, not OS)
- **Working directory:** Set at invocation. Bash commands run relative to it, but **shell state does NOT persist** between Bash calls — use absolute paths
- **No built-in sandbox:** Claude is instructed to avoid destructive ops, but there's no OS-level restriction

---

## 4. Shell / Bash Execution

- Runs via user's shell (`zsh` on macOS)
- Environment initialized from user profile
- **`CLAUDECODE` env var is stripped** before spawning any subprocess — critical to prevent "cannot launch inside another Claude Code session" error
- No network or filesystem sandbox
- Timeout: default 120s, max 600s
- `run_in_background: true` for long-running commands

---

## 5. Context Window & Memory

- **~200K tokens** effective context (claude-sonnet-4-5)
- System prompt + conversation history + tool results all count
- **Auto-compression:** System compresses prior messages as context fills
- **Sub-agent isolation:** Each Task sub-agent has its own fresh context — no context bleed, but also no shared state
- **Cross-session persistence:** Standard `-p` invocations are stateless. Memory must be written to files explicitly

---

## 6. Parallel Execution

**Within a single turn:** Multiple tool calls in one response execute in parallel if independent (e.g., 5 Read calls simultaneously).

**Across turns:** Sequential — each turn waits for all tool results before next LLM call.

**Recommended parallel pattern:**
```python
# Orchestrator spawns parallel background agents
# Task 1: write solution     [background]
# Task 2: write tests        [background]
# Task 3: research approach  [background]
# → wait for all → synthesize
```

---

## 7. What Claude Cannot Do

| Limitation | Notes |
|-----------|-------|
| No persistent memory between `-p` invocations | Write to files explicitly |
| No real-time streaming output in `-p` mode | Caller gets final result only |
| No inter-agent communication | Sub-agents can only return to parent |
| AskUserQuestion is useless in `-p` mode | Never depend on mid-run user input |
| No browser automation | WebFetch = simple HTTP + HTML→markdown |
| WebFetch fails for authenticated URLs | Google Docs, GitHub private, Confluence, etc. |
| WebSearch is US-only | |
| Bash shell state doesn't persist | Each Bash call = fresh shell |

### Common Failure Modes

| Failure | Cause | Fix |
|---------|-------|-----|
| `claude` refuses to start | `CLAUDECODE` env var set | Strip it (handled in `base_agent.py`) |
| Empty stdout | Some CLIs write to stderr on success | Fall back to stderr (handled in `base_agent.py`) |
| Edit fails "not unique" | `old_string` matches multiple places | Provide more surrounding context |
| Context overflow | Too many files in main context | Use Explore sub-agents; paginate large files |
| Tool not found | `--allowedTools` whitelist too restrictive | Audit which tools each agent needs |

---

## 8. Best Practices for Max Performance

### Prompt Patterns
- Be explicit about output format — stdout is the return value in `-p` mode
- Provide absolute file paths, not descriptions
- Front-load constraints (output format, files to touch, what NOT to do)
- Use numbered steps for multi-stage tasks

### For Complex Multi-Step Tasks
```
1. "Do these three things in order:
    1. Read X, identify Y
    2. Check Z against Y
    3. Output a markdown table: ..."
```

### For Autonomous Coding (this repo's use case)
- Pass `cwd=workspace.path` so agents use relative paths
- Use `--allowedTools Bash,Write,Read,Edit,Glob,Grep,Task` for full autonomy
- Hint at sub-agent use for tasks with independent components:
  - *"If this task has independent components, consider using the Task tool to develop them in parallel"*
- Reviewer and Critic calls are **independent** — parallelize them

### For Parallelism
```bash
# Spawn multiple background agents, collect with TaskOutput
# Or externally: multiple claude -p subprocess calls simultaneously
```

---

## 9. CLI Flags & Options

```bash
# Non-interactive mode
claude -p "<prompt>"                  # prompt as argument
claude -p                             # read prompt from stdin

# Key flags
--output-format text|json|stream-json  # output serialization
--allowedTools "Bash,Write,..."        # whitelist tools
--max-turns <n>                        # cap agentic turns
--model <model-id>                     # e.g. claude-opus-4-6
--mcp-config <path>                    # JSON file for MCP servers
--system-prompt <text>                 # override system prompt
--append-system-prompt <text>          # append to system prompt
--no-cache                             # disable prompt caching
--verbose                              # more detailed logging
--dangerously-skip-permissions         # skip all permission prompts
```

### Output Format Options

| Format | Description | Best for |
|--------|-------------|---------|
| `text` | Plain text (default) | Human-readable output, piping |
| `json` | Structured JSON with metadata | Programmatic parsing |
| `stream-json` | Newline-delimited JSON stream | Real-time processing |

---

## Key Architectural Insight

**Claude in `-p` mode is stateless between invocations.** Every call starts fresh. State must live in the orchestrator (Python/shell), not in Claude.

**`CLAUDECODE` env var stripping is mandatory** when calling `claude -p` from within a Claude Code session. Already handled in `base_agent.py:BaseAgent.run()`.
