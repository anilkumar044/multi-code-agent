"""
agents/reviewer_agent.py

Reviewer agent — reviews code quality, bugs, security, performance.
Default CLI: codex  (invoked as: codex exec --skip-git-repo-check "prompt")
"""

from .base_agent import BaseAgent

_COMMANDS = {
    "codex":  lambda p: ["codex", "exec", "--skip-git-repo-check", p],
    "claude": lambda p: ["claude", "-p", p, "--allowedTools", "Bash,Write,Read,Edit,Glob,Grep,Task"],
    "gemini": lambda p: ["gemini", "--approval-mode", "yolo", "-p", p],
}


class ReviewerAgent(BaseAgent):
    ROLE = "Reviewer"
    COLOR = "green"

    def build_command(self, prompt: str) -> list[str]:
        builder = _COMMANDS.get(self.cli)
        if builder is None:
            raise ValueError(f"Unsupported CLI for ReviewerAgent: {self.cli!r}")
        return builder(prompt)
