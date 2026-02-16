"""
agents/critic_agent.py

Critic agent — challenges the review, finds missed issues, flags false positives.
Default CLI: gemini  (invoked as: gemini -p "prompt")
"""

from .base_agent import BaseAgent

_COMMANDS = {
    "gemini": lambda p: ["gemini", "-p", p],
    "claude": lambda p: ["claude", "-p", p, "--allowedTools", "Bash,Read,Glob,Grep"],
    "codex":  lambda p: ["codex", "exec", "--skip-git-repo-check", p],
}


class CriticAgent(BaseAgent):
    ROLE = "Critic"
    COLOR = "magenta"

    def build_command(self, prompt: str) -> list[str]:
        builder = _COMMANDS.get(self.cli)
        if builder is None:
            raise ValueError(f"Unsupported CLI for CriticAgent: {self.cli!r}")
        return builder(prompt)
