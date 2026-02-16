"""
agents/base_agent.py

Abstract base class for all agents.
Each agent wraps a specific CLI tool and exposes a single run(prompt) method.
"""

import os
import shutil
import subprocess
from abc import ABC, abstractmethod


class AgentError(Exception):
    """Raised when an agent call fails irrecoverably."""


class AgentTimeoutError(AgentError):
    pass


class CLINotFoundError(AgentError):
    pass


class EmptyResponseError(AgentError):
    pass


class BaseAgent(ABC):
    """
    Abstract agent backed by an external CLI tool.

    Concrete subclasses define:
      ROLE:  human-readable role name ("Creator", "Reviewer", "Critic")
      COLOR: rich style string ("cyan", "green", "magenta")
      build_command(prompt): returns the argv list to pass to subprocess
    """

    ROLE: str = "Agent"
    COLOR: str = "white"

    def __init__(self, cli: str, timeout: int, display):
        self.cli = cli
        self.timeout = timeout
        self.display = display

    @abstractmethod
    def build_command(self, prompt: str) -> list[str]:
        """Return the argv list for subprocess.run(). Prompt is a CLI argument."""
        ...

    def run(self, prompt: str, cwd: "Path | None" = None) -> str:
        """Execute the CLI tool with the given prompt and return its response."""
        cmd = self.build_command(prompt)

        # Strip CLAUDECODE so claude can be invoked as a subprocess from inside
        # an existing Claude Code session (which would otherwise block it).
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env=env,
                cwd=str(cwd) if cwd is not None else None,
            )
        except subprocess.TimeoutExpired:
            raise AgentTimeoutError(
                f"{self.ROLE} ({self.cli}) timed out after {self.timeout}s. "
                "Try increasing --timeout."
            )
        except FileNotFoundError:
            raise CLINotFoundError(
                f"CLI binary '{self.cli}' not found. Is it installed and in PATH?"
            )

        # Prefer stdout; fall back to stderr for tools that write there on success
        output = result.stdout.strip()
        if not output and result.stderr.strip():
            output = result.stderr.strip()

        if not output:
            raise EmptyResponseError(
                f"{self.ROLE} ({self.cli}) returned an empty response. "
                f"Exit code: {result.returncode}. "
                f"Stderr: {result.stderr[:300]!r}"
            )

        return output

    def is_available(self) -> bool:
        return shutil.which(self.cli) is not None
