# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the system

```bash
# Install the single dependency
pip install -r requirements.txt

# Basic run (Claude=Creator, Codex=Reviewer, Gemini=Critic, 3 cycles)
python main.py "write a binary search function"

# Save final code to file
python main.py "implement quicksort" --output quicksort.py

# Custom role assignment
python main.py "build a rate limiter" --creator gemini --reviewer claude --critic openai

# Fewer cycles, longer timeout
python main.py "write a merge sort" --iterations 2 --timeout 180

# Skip saving session JSON
python main.py "fibonacci sequence" --no-save
```

## Architecture

The system orchestrates three external AI CLIs in a feedback loop. All control flow lives in `core/orchestrator.py`; all state lives in `core/session.py`.

**Feedback loop** (one run = Phase 0 + N cycles):
```
Phase 0:  Creator  → initial code
Cycle i:  Reviewer → reviews current code   (uses prior-cycle critique as context on cycle 2+)
          Critic   → challenges the review  (finds missed issues, flags false positives)
          Creator  → revises code           (weighs both review and critic's perspective)
```

**Key design decisions:**
- Every agent call is stateless (single subprocess invocation). Context is re-injected via prompt construction in `prompts/templates.py` — `PromptBuilder` has five methods: `creator_initial`, `creator_revision`, `reviewer_initial`, `reviewer_update`, `critic`.
- `Session` (core/session.py) is the single source of truth. Properties `current_code`, `previous_review`, and `current_critique` compute the right slice of history for each prompt phase. `current_critique` returns the *prior* iteration's critique (so the Reviewer on cycle 2 can update its stance).
- All display output is routed through `display/console.py` (`ConsoleDisplay`). The orchestrator and agents never call `print` directly.
- `BaseAgent.run()` in `agents/base_agent.py` falls back to stderr if stdout is empty, because some CLIs write to stderr on success. All three error types (`AgentTimeoutError`, `CLINotFoundError`, `EmptyResponseError`) are subclasses of `AgentError` so the orchestrator can catch them uniformly.
- `BaseAgent.run()` strips `CLAUDECODE` from the subprocess environment before spawning any CLI. This is required when running from inside a Claude Code session — without it, the `claude` binary refuses to start with "Claude Code cannot be launched inside another Claude Code session".

**CLI invocations per agent:**

| Key | Binary | Non-interactive command |
|-----|--------|------------------------|
| `claude` | `claude` | `claude -p "<prompt>"` |
| `openai` | `codex`  | `codex exec --skip-git-repo-check "<prompt>"` |
| `gemini` | `gemini` | `gemini -p "<prompt>"` |

The mapping from user-facing key (`claude`/`openai`/`gemini`) to binary name lives in `agents/__init__.py` (`TOOL_MAP`). Each concrete agent class (`creator_agent.py`, `reviewer_agent.py`, `critic_agent.py`) has its own `_COMMANDS` dict mapping binary → argv builder, so role assignment is fully flexible.

## Adding a new agent / CLI tool

1. Add its binary name and argv builder to `_COMMANDS` in all three agent class files.
2. Add it to `TOOL_MAP` in `agents/__init__.py`.
3. Add its install hint to `_TOOL_INFO` in `core/availability.py`.
4. Add its display label to `_CLI_LABELS` in `display/console.py`.
5. Add the new key to `choices=` in `main.py`'s three `--creator/--reviewer/--critic` arguments.

## Modifying prompts

All prompt text is in `prompts/templates.py` (`PromptBuilder`). The five methods map directly to the five call types in the loop. The Creator's revision prompt receives both `review` and `critique` so it can balance reviewer and critic perspectives — be careful not to bias it too heavily toward either.

## Session transcripts

Saved to `./sessions/session_YYYYMMDD_HHMMSS.json`. The schema records `initial_code`, `final_code`, and per-iteration `review`/`critique`/`revision` strings. Useful for debugging prompt quality or replaying a run offline.
