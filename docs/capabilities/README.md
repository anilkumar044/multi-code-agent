# Agent Capability Reference

Each tool was queried directly about its own capabilities. This directory contains the resulting documentation.

| File | Tool | Model |
|------|------|-------|
| [claude.md](claude.md) | `claude` CLI | claude-sonnet-4-5-20250929 |
| [codex.md](codex.md) | `codex` CLI | gpt-5.3-codex |
| [gemini.md](gemini.md) | `gemini` CLI | Gemini 2.x |

---

## Capability Comparison Matrix

| Capability | Claude | Codex | Gemini |
|-----------|--------|-------|--------|
| **Context window** | ~200K tokens | Model-dependent | Up to 1M tokens |
| **File read** | ✓ (Read tool, abs paths) | ✓ (exec_command) | ✓ (read_file, paginated) |
| **File write** | ✓ (Write/Edit tools) | ✓ (apply_patch) | ✓ (write_file if enabled, else via shell) |
| **Shell execution** | ✓ (Bash tool) | ✓ (exec_command) | ✓ (run_shell_command) |
| **Web search** | ✓ (WebSearch, US-only) | ✓ (web.search_query) | ✓ (google_web_search) |
| **Web browse** | Fetch only (no JS) | ✓ (web.open/click/find) | Search only |
| **Parallel tool calls** | ✓ (within turn) | ✓ (multi_tool_use.parallel) | ✓ (within turn) |
| **Sub-agent spawning** | ✓ (Task tool, parallel bg) | External only | Limited (specialized sub-agents) |
| **Session memory** | Files only (stateless) | ✓ (~/.codex/sessions) | ✓ (--resume, save_memory) |
| **Sandbox mode** | None (instructions-based) | ✓ (Seatbelt/Landlock, 3 levels) | ✓ (--sandbox Docker-like) |
| **Approval modes** | --allowedTools whitelist | 4 levels (-a flag) | 4 modes (--approval-mode) |
| **MCP integration** | ✓ (--mcp-config) | ✓ (codex mcp add) | ✓ (--allowed-mcp-server-names) |
| **Structured output** | json, stream-json | --json (JSONL), --output-schema | json, stream-json |
| **Image input** | ✓ (Read tool) | ✓ (view_image, -i flag) | ✓ (read_file) |
| **Cloud/remote tasks** | — | ✓ (codex cloud exec) | — |

---

## Role Assignment Rationale

### Creator → Claude
**Why:** Best sub-agent spawning (Task tool with parallel background agents), strongest file manipulation tools (Read/Write/Edit with safety guarantees), explicit `--allowedTools` control. Best suited for long autonomous coding sessions.

**Best flags:**
```bash
claude -p "..." --allowedTools "Bash,Write,Read,Edit,Glob,Grep,Task"
```
**Key strength:** Can spawn parallel sub-agents to develop independent components simultaneously.

---

### Reviewer → Codex
**Why:** `codex exec review` is a purpose-built code review subcommand. `apply_patch` enables precise surgical file edits. Strong shell execution for running tests and linters.

**Best flags:**
```bash
codex -a never exec \
  --skip-git-repo-check \
  --sandbox workspace-write \
  -C /path/to/workspace \
  --ephemeral \
  "prompt"
```
**Key strength:** Can read files, run tests, and write structured review output — all within one autonomous run.

---

### Critic → Gemini
**Why:** Massive context window (1M tokens) means it can hold the entire history — all code, all reviews, all prior critiques — simultaneously. `google_web_search` gives access to real-time information for checking current best practices, CVEs, etc.

**Best flags:**
```bash
gemini --approval-mode yolo -p "..."
```
**Key strength:** Never truncates context. Ideal for the holistic "evaluate everything at once" role.

---

## What We're NOT Yet Using (Next Level Opportunities)

### Claude
- `Task` tool with `run_in_background: true` for parallel component development
- `WebSearch` + `WebFetch` for researching libraries during implementation
- `stream-json` output format for real-time progress display
- Multiple specialized sub-agent types (Explore for codebase analysis, Plan for architecture)

### Codex
- `codex exec review --uncommitted` for reviewing staged changes
- `codex cloud exec --attempts N` for parallel cloud-side attempts
- `--output-schema <file>` for enforcing structured JSON output from the reviewer
- `-o, --output-last-message <file>` for cleaner output capture
- `codex exec resume` for multi-turn conversations across orchestrator cycles
- `--sandbox workspace-write` for proper sandboxed autonomy

### Gemini
- `--resume latest` to maintain context across orchestrator cycles (give Gemini memory of prior critiques)
- `--output-format stream-json` for real-time critique streaming
- `save_memory` for persisting project-specific preferences across sessions
- `codebase_investigator` sub-agent for deep structural analysis
- `google_web_search` in prompts to check current security advisories, lib versions

### Cross-Agent
- **Parallelizing Reviewer + Critic:** They're independent once Creator output is ready — run simultaneously
- **Structured output parsing:** Use `--output-format json` or `--output-schema` to get machine-parseable reviews instead of free-text
- **Session continuity:** Codex `--resume` and Gemini `--resume` could maintain context across cycles instead of re-injecting everything via prompts
- **MCP servers:** A shared MCP server could provide all agents with real-time access to the workspace without needing `cwd` injection
