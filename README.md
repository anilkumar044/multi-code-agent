# Multi-Agent Code Generator

Three AI agents collaborate in a feedback loop to iteratively improve code:

| Role | Default Agent | Job |
|------|--------------|-----|
| **Creator** | Claude | Writes initial code, revises based on feedback |
| **Reviewer** | Codex | Reviews quality, bugs, security, performance |
| **Critic** | Gemini | Challenges the review — missed issues, false positives, priority calibration |

## How it works

```
Phase 0:  Creator → initial code

Cycle 1:  Reviewer → reviews code
          Critic   → challenges the review
          Creator  → revises code (using both review + critic's perspective)

Cycle 2:  Reviewer → updates review (aware of critic's prior challenge + new code)
          Critic   → challenges updated review
          Creator  → revises again

Cycle 3:  (same pattern)

Output:   Final revised code  +  session JSON transcript
```

## Prerequisites

All three CLI tools must be installed and authenticated:

```bash
# Claude Code
npm install -g @anthropic-ai/claude-code
claude          # authenticate on first run

# OpenAI Codex CLI
npm install -g @openai/codex
codex           # set OPENAI_API_KEY or authenticate

# Google Gemini CLI
npm install -g @google/gemini-cli
gemini          # authenticate on first run
```

## Installation

```bash
cd multi-code-agent
pip install -r requirements.txt
```

## Usage

```bash
# Basic — uses default agents (Claude=Creator, Codex=Reviewer, Gemini=Critic)
python main.py "write a binary search function"

# Save final code to a file
python main.py "implement quicksort" --output quicksort.py

# Custom role assignment
python main.py "build a rate limiter" \
  --creator gemini --reviewer claude --critic openai

# Change number of cycles (default: 3)
python main.py "implement an LRU cache" --iterations 2

# Increase timeout for complex tasks (default: 120s per agent call)
python main.py "implement a REST API client" --timeout 180

# Skip saving session JSON
python main.py "fibonacci sequence" --no-save

# All options
python main.py --help
```

## Session transcripts

Each run saves a JSON transcript to `./sessions/session_YYYYMMDD_HHMMSS.json`:

```json
{
  "id": "session_20260216_143022",
  "task": "write a binary search function",
  "config": {"creator": "claude", "reviewer": "codex", "critic": "gemini", "iterations": 3},
  "initial_code": "...",
  "final_code": "...",
  "iterations": [
    {
      "number": 1,
      "review": "...",
      "critique": "...",
      "revision": "..."
    }
  ]
}
```

## CLI note on agent invocations

| Agent | CLI binary | Non-interactive invocation |
|-------|-----------|---------------------------|
| Claude | `claude` | `claude -p "prompt"` |
| Codex  | `codex`  | `codex exec --skip-git-repo-check "prompt"` |
| Gemini | `gemini` | `gemini -p "prompt"` |
