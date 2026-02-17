"""
agents/base_agent.py

Abstract base class for all agents.
Each agent wraps a specific CLI tool and exposes a single run(prompt) method.
"""

import os
import shutil
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


_FALLBACK_TRIGGERS = frozenset([
    "error_max_tokens",          # Claude JSON subtype
    "context_length_exceeded",   # OpenAI error code
    "maximum context length",    # OpenAI message
    "prompt is too long",
    "resource_exhausted",        # Gemini gRPC status
    "model_capacity_exhausted",  # Gemini metadata
    "no capacity available",     # Gemini human message
    "rate limit exceeded",
    "too many requests",
    "context window",
])


class AgentError(Exception):
    """Raised when an agent call fails irrecoverably."""


class AgentTimeoutError(AgentError):
    pass


class CLINotFoundError(AgentError):
    pass


class EmptyResponseError(AgentError):
    pass


class TokenLimitError(AgentError):
    """Token/context limit or model capacity exhausted — triggers model fallback."""


@dataclass
class AgentResponse:
    text: str
    session_id: str = ""


class BaseAgent(ABC):
    """
    Abstract agent backed by an external CLI tool.

    Concrete subclasses define:
      ROLE:  human-readable role name ("Creator", "Reviewer", "Critic")
      COLOR: rich style string ("cyan", "green", "magenta")
      build_command(prompt, model, session_id): returns the argv list to pass to subprocess
    """

    ROLE: str = "Agent"
    COLOR: str = "white"

    def __init__(self, cli: str, timeout: int, display):
        self.cli = cli
        self.timeout = timeout
        self.display = display
        self._session_id: str = ""            # populated after first successful call
        self._current_model: str = ""         # set by subclass __init__
        self._fallback_models: list[str] = [] # set by subclass __init__

    @abstractmethod
    def build_command(self, prompt: str, model: str = "", session_id: str = "") -> list[str]:
        """Return the argv list for subprocess.run(). Prompt is a CLI argument."""
        ...

    def parse_output(self, raw: str) -> AgentResponse:
        """Parse raw CLI output. Default checks for fallback triggers in raw text."""
        if any(t in raw.lower() for t in _FALLBACK_TRIGGERS):
            raise TokenLimitError(f"{self.ROLE} ({self.cli}) hit token/capacity limit")
        return AgentResponse(text=raw)

    def _get_model_chain(self) -> list[str]:
        chain = [self._current_model] if self._current_model else [""]
        for m in self._fallback_models:
            if m not in chain:
                chain.append(m)
        return chain

    def run(self, prompt: str, cwd: "Path | None" = None) -> str:
        """Execute the CLI tool with the given prompt and return its response."""
        models = self._get_model_chain()
        last_exc: Exception = EmptyResponseError(f"{self.ROLE} produced no output")
        for i, model in enumerate(models):
            is_retry = i > 0
            # On fallback: fresh session (different model cannot resume prior session)
            sid = "" if is_retry else self._session_id
            if is_retry:
                self.display.error(
                    f"{self.ROLE} ({self.cli}): {models[i-1] or 'default'} hit limit "
                    f"— retrying with {model or 'default'}"
                )
            try:
                cmd = self.build_command(prompt, model=model, session_id=sid)
                raw = self._execute(cmd, cwd)
                response = self.parse_output(raw)
                if response.session_id:
                    self._session_id = response.session_id
                if model:
                    self._current_model = model
                return response.text
            except TokenLimitError as exc:
                last_exc = exc
                if i < len(models) - 1:
                    continue
                raise
            except AgentError:
                raise
        raise last_exc

    def _execute(self, cmd: list[str], cwd) -> str:
        """Clean subprocess execution — no fallback detection."""
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
