# Codex CLI (`codex exec`) — Capability Reference

*Self-reported on 2026-02-16, verified against codex-cli v0.101.0 with gpt-5.3-codex model.*

---

## 1. Available Tools (Agent Tool Surface)

| Tool | What it does | Key Params | Limits |
|------|-------------|------------|--------|
| `exec_command` | Run shell command | `cmd`, `workdir`, `yield_time_ms`, `max_output_tokens`, `tty`, `shell`, `login` | Subject to sandbox + approval policy; output truncatable |
| `write_stdin` | Send input to running shell session | `session_id`, `chars`, `yield_time_ms`, `max_output_tokens` | Only for sessions started via `exec_command` |
| `apply_patch` | Structured file patch edits | patch text in strict grammar | Fails if FS is read-only or path not writable |
| `list_mcp_resources` | List MCP resources | optional `server`, `cursor` | Only configured MCP servers |
| `read_mcp_resource` | Read MCP resource content | `server`, `uri` | URI must exist from list results |
| `update_plan` | Maintain explicit task plan | `plan[]`, explanation | One step in progress at a time |
| `request_user_input` | Structured user questions | 1-3 questions with options | Only in Plan mode |
| `view_image` | Load local image for analysis | `path` | Needs filesystem read access |
| `multi_tool_use.parallel` | Run multiple tools concurrently | list of `functions.*` calls | Only for independent calls |
| `web.search_query` | Web search | up to 4 queries/call | For >3 queries, needs medium/long response |
| `web.open` / `click` / `find` | Navigate and inspect web pages | `ref_id`, link ids, patterns | Needs prior search/open refs |
| `web.screenshot` | PDF page capture | `ref_id`, `pageno` | PDF-only, page-indexed |

### CLI Subcommands

- `exec` — non-interactive agent run
- `exec review` — non-interactive code review
- `exec resume` — resume prior session non-interactively
- `resume` / `fork` — continue/fork prior sessions (interactive)
- `apply` — apply a task diff to local git tree via `git apply`
- `mcp` / `mcp-server` — manage/run MCP integrations
- `sandbox` — run OS commands under Codex sandbox (Seatbelt/Landlock)
- `cloud` *(experimental)* — remote Codex Cloud task lifecycle
- `features` — list/enable/disable feature flags
- `login` / `logout` — auth management

---

## 2. Agentic / Autonomous Capabilities

- **Multi-step workflows:** Yes — plan, inspect files, run commands, evaluate results, revise, and continue within one run
- **Self-correction:** Yes — reacts to tool errors and retries alternative commands
- **Built-in retry:** Yes — automatic reconnect attempts (up to 5) on upstream stream failures
- **Parallel tool calls:** Yes, via `multi_tool_use.parallel` for independent calls within a single turn
- **Parallel workers:** Not built-in for a single `codex exec`. Use **external orchestration** (multiple `codex exec` subprocesses) for true parallelism
- **Codex Cloud attempts:** `codex cloud exec --attempts N` provides best-of-N cloud attempts in parallel at the service level

---

## 3. File System Operations

| Sandbox Mode | Read | Write | Notes |
|-------------|------|-------|-------|
| `read-only` | ✓ | ✗ | No file writes at all |
| `workspace-write` | ✓ | ✓ (workdir + temp) | `--add-dir` extends writable roots |
| `danger-full-access` | ✓ | ✓ (anywhere) | No FS restriction |

- **Working directory:** Set via `-C/--cd`. In `workspace-write`, writable roots anchored to workdir
- **`--skip-git-repo-check`:** Without it, Codex refuses to run outside a trusted git repo. With it, runs anywhere but git-aware features degrade
- **`--add-dir <DIR>`:** Explicitly add an extra writable/readable root outside workdir

---

## 4. Shell / Bash Execution

- Any installed command reachable in environment, constrained by sandbox + approval policy
- **Sandboxing mechanisms:**
  - macOS: Seatbelt (Apple Sandbox)
  - Linux: Landlock + seccomp
  - Windows: Restricted token
- **Approval policy** determines whether commands run automatically or require escalation
- **Environment:** Inherited from shell by default; configurable via `shell_environment_policy` in config
- Auth stored in `~/.codex/`

---

## 5. Context Window & Memory

- Context size is model-dependent; not exposed as a fixed CLI flag
- **Large codebase handling:** Incremental file discovery (`rg`, selective reads) — not whole-repo ingestion
- **Session persistence:** Persistent by default in `~/.codex/sessions/` and history files
- **`--ephemeral`:** Disables session persistence for stateless runs
- **Resume/Fork:** `codex exec resume` and `codex fork` reuse prior thread context
- **Context compaction:** Supported internally for long conversations

---

## 6. Approval Modes

> **Important:** Approval flags are **global flags** — place them before `exec`, not after:
> ```bash
> codex -a never exec --skip-git-repo-check "..."   # ✓ correct
> codex exec --ask-for-approval never "..."          # ✗ rejected
> ```

| Policy (`-a` / `--ask-for-approval`) | Behavior |
|--------------------------------------|----------|
| `untrusted` | Trusted commands auto-run; others require approval |
| `on-failure` | Run commands; ask only on escalation after failure |
| `on-request` | Model decides when to ask |
| `never` | Never ask; failures returned directly |

**Convenience aliases:**
- `--full-auto` → `-a on-request --sandbox workspace-write` (low-friction sandboxed autonomy)
- `--dangerously-bypass-approvals-and-sandbox` → no approvals + no sandbox (high risk)

**Fully autonomous operation:**
```bash
# Sandboxed autonomy (safer)
codex -a never exec --sandbox workspace-write --skip-git-repo-check "..."

# Unsandboxed autonomy (maximum capability, use with care)
codex exec --dangerously-bypass-approvals-and-sandbox --skip-git-repo-check "..."
```

---

## 7. What Codex Cannot Do

| Limitation | Notes |
|-----------|-------|
| `--approval-mode` is NOT a valid `exec` flag | Use global `-a` before `exec` |
| Network availability not guaranteed | Hits chatgpt.com API; can disconnect; 5 auto-retries then fails |
| Output not deterministic | Natural-language; use `--output-schema` to constrain shape |
| No built-in fan-out parallelism | Orchestrate multiple `codex exec` processes externally |
| `--json` output is not always clean | Warnings/log lines appear alongside JSONL events — parse defensively |
| git context required by default | Use `--skip-git-repo-check` for non-repo dirs |
| Host policy overrides CLI flags | Sandbox/approval limits can be hard-overridden by host environment |

---

## 8. Best Practices for Max Performance

1. **Explicit objective + constraints + touched paths + "done when" checklist** in the prompt
2. **Pin settings in automation:** model (`-m`), cwd (`-C`), sandbox, approval, `--skip-git-repo-check`
3. **For non-interactive robustness:**
   ```bash
   codex -a never exec \
     --skip-git-repo-check \
     --sandbox workspace-write \
     -C /path/to/workspace \
     --ephemeral \
     --json \
     --color never \
     -o /path/to/last_message.txt \
     "your prompt"
   ```
4. **Parse JSONL defensively** — filter for JSON records, handle non-zero exits, retry transient failures
5. **External orchestration for parallelism** — multiple `codex exec` subprocess calls, not expecting one run to fan out
6. **For code review specifically:** `codex exec review` is a purpose-built subcommand with `--uncommitted` flag for staged/unstaged/untracked changes

---

## 9. `codex exec` Full Flag Reference (v0.101.0)

```bash
# Exec-level options
codex exec [OPTIONS] [PROMPT]
  -c, --config <key=value>                  Override config.toml values (dotted path)
  --enable <FEATURE>                         Enable feature flag
  --disable <FEATURE>                        Disable feature flag
  -i, --image <FILE>...                      Attach image files
  -m, --model <MODEL>                        Override model
  --oss                                      Use open-source model
  --local-provider <lmstudio|ollama>         Use local LLM provider
  -s, --sandbox <read-only|workspace-write|danger-full-access>
  -p, --profile <CONFIG_PROFILE>             Named config profile
  --full-auto                                Sandboxed, low-friction autonomy
  --dangerously-bypass-approvals-and-sandbox No approvals, no sandbox
  -C, --cd <DIR>                             Set working directory
  --skip-git-repo-check                      Allow running outside git repos
  --add-dir <DIR>                            Add extra writable/readable root
  --ephemeral                                Disable session persistence
  --output-schema <FILE>                     JSON schema for structured output
  --color <always|never|auto>                Color output control
  --json                                     JSONL output mode
  -o, --output-last-message <FILE>           Write last agent message to file

# Global flags (must be placed BEFORE 'exec')
codex -a <POLICY> exec ...
  -a, --ask-for-approval <untrusted|on-failure|on-request|never>
  --search                                   Enable web_search tool
```

### `codex exec review` (code review subcommand)

```bash
codex exec review [OPTIONS] [PROMPT]
  --uncommitted    Review staged, unstaged, and untracked changes
```

### `codex cloud exec` (experimental remote tasks)

```bash
codex cloud exec --env <ENV_ID> [QUERY]
  --attempts <N>   Submit N parallel attempts, return best result
```

---

## Config File (`~/.codex/config.toml`)

```toml
model = "gpt-5.3-codex"
model_reasoning_effort = "xhigh"
personality = "pragmatic"

[projects."/path/to/project"]
trust_level = "trusted"
```

Override any value at runtime: `codex -c model="o3" exec ...`

---

## Key Architectural Insight

Codex's agentic power is in `exec_command` + `apply_patch` — it can run tests, observe results, fix code, and repeat, all within one `codex exec` invocation. The key lever is **approval mode** (`-a never`) + **sandbox mode** (`--sandbox workspace-write`) to allow fully autonomous file writes and command execution without human intervention.

Network reliability is the main operational risk — build retry logic in the outer orchestrator.
