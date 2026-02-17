"""
agents/creator_agent.py

Creator agent — writes and revises code.
Default CLI: claude  (invoked as: claude --output-format json -p "prompt")
"""

import re

from .base_agent import BaseAgent, AgentResponse
from .parsers import parse_claude_json, parse_codex_jsonl, parse_gemini_json

# Maps CLI -> (primary_model, fallback_models)
_MODEL_CHAINS: dict[str, tuple[str, list[str]]] = {
    "claude": ("claude-sonnet-4-5-20250929", ["claude-haiku-4-5-20251001"]),
    "codex":  ("gpt-5.3-codex",              ["o4-mini"]),
    "gemini": ("gemini-2.5-pro",             ["gemini-2.5-flash", "gemini-2.5-flash-lite"]),
}

# Matches an optional opening ```<lang> fence and/or a closing ``` fence
_FENCE_RE = re.compile(r"^```[\w]*\n?|\n?```$", re.MULTILINE)


def _strip_fences(text: str) -> str:
    """Remove markdown code fences that some LLMs add despite being told not to."""
    return _FENCE_RE.sub("", text).strip()


class CreatorAgent(BaseAgent):
    ROLE = "Creator"
    COLOR = "cyan"

    def __init__(self, cli: str, timeout: int, display):
        super().__init__(cli, timeout, display)
        self._current_model, self._fallback_models = _MODEL_CHAINS.get(cli, ("", []))

    def build_command(self, prompt: str, model: str = "", session_id: str = "") -> list[str]:
        if self.cli == "claude":
            cmd = ["claude", "--output-format", "json"]
            if model:
                cmd += ["--model", model]
            if session_id:
                cmd += ["--resume", session_id]
            cmd += ["-p", prompt, "--allowedTools", "Bash,Write,Read,Edit,Glob,Grep,Task"]
            return cmd

        if self.cli == "codex":
            if session_id:
                cmd = ["codex", "exec"]
                if model:
                    cmd += ["-m", model]
                cmd += ["resume", "--json", "--skip-git-repo-check", session_id, prompt]
            else:
                cmd = ["codex"]
                if model:
                    cmd += ["-m", model]
                cmd += ["exec", "--json", "--skip-git-repo-check", prompt]
            return cmd

        if self.cli == "gemini":
            cmd = ["gemini", "--output-format", "json"]
            if model:
                cmd += ["--model", model]
            # NOTE: session_id is NOT used as --resume value for gemini
            # (only accepts "latest"/index). UUID stored for tracking only.
            cmd += ["-p", prompt]
            return cmd

        raise ValueError(f"Unsupported CLI for CreatorAgent: {self.cli!r}")

    def parse_output(self, raw: str) -> AgentResponse:
        if self.cli == "claude":
            return parse_claude_json(raw)
        if self.cli == "codex":
            return parse_codex_jsonl(raw)
        if self.cli == "gemini":
            return parse_gemini_json(raw)
        return AgentResponse(text=raw)

    def run(self, prompt: str, cwd=None) -> str:
        return _strip_fences(super().run(prompt, cwd=cwd))
