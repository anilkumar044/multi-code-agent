"""
agents/creator_agent.py

Creator agent — writes and revises code.
Default CLI: claude  (invoked as: claude -p "prompt")
"""

import re

from .base_agent import BaseAgent

# Maps CLI binary name -> argv builder
_COMMANDS = {
    "claude": lambda p: ["claude", "-p", p, "--allowedTools", "Bash,Write,Read,Edit,Glob,Grep,Task"],
    "codex":  lambda p: ["codex", "exec", "--skip-git-repo-check", "--approval-mode", "full-auto", p],
    "gemini": lambda p: ["gemini", "-p", p],
}

# Matches an optional opening ```<lang> fence and/or a closing ``` fence
_FENCE_RE = re.compile(r"^```[\w]*\n?|\n?```$", re.MULTILINE)


def _strip_fences(text: str) -> str:
    """Remove markdown code fences that some LLMs add despite being told not to."""
    return _FENCE_RE.sub("", text).strip()


class CreatorAgent(BaseAgent):
    ROLE = "Creator"
    COLOR = "cyan"

    def build_command(self, prompt: str) -> list[str]:
        builder = _COMMANDS.get(self.cli)
        if builder is None:
            raise ValueError(f"Unsupported CLI for CreatorAgent: {self.cli!r}")
        return builder(prompt)

    def run(self, prompt: str, cwd=None) -> str:
        return _strip_fences(super().run(prompt, cwd=cwd))
