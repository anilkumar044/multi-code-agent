"""
agents/critic_agent.py

Critic agent — challenges the review, finds missed issues, flags false positives.
Default CLI: gemini  (invoked as: gemini --output-format json -p "prompt")
"""

from .base_agent import BaseAgent, AgentResponse
from .parsers import parse_claude_json, parse_codex_jsonl, parse_gemini_json

# Maps CLI -> (primary_model, fallback_models)
_MODEL_CHAINS: dict[str, tuple[str, list[str]]] = {
    "claude": ("claude-sonnet-4-5-20250929", ["claude-haiku-4-5-20251001"]),
    "codex":  ("gpt-5.3-codex",              ["o4-mini"]),
    "gemini": ("gemini-2.5-pro",             ["gemini-2.5-flash", "gemini-2.5-flash-lite"]),
}


class CriticAgent(BaseAgent):
    ROLE = "Critic"
    COLOR = "magenta"

    def __init__(self, cli: str, timeout: int, display):
        super().__init__(cli, timeout, display)
        self._current_model, self._fallback_models = _MODEL_CHAINS.get(cli, ("", []))

    def build_command(self, prompt: str, model: str = "", session_id: str = "") -> list[str]:
        if self.cli == "gemini":
            cmd = ["gemini", "--approval-mode", "yolo", "--output-format", "json"]
            if model:
                cmd += ["--model", model]
            # session_id acts as truthy flag only — gemini only accepts "latest"/index
            if session_id:
                cmd += ["--resume", "latest"]
            cmd += ["-p", prompt]
            return cmd

        if self.cli == "claude":
            cmd = ["claude", "--output-format", "json"]
            if model:
                cmd += ["--model", model]
            if session_id:
                cmd += ["--resume", session_id]
            cmd += ["-p", prompt, "--allowedTools", "Bash,Read,Glob,Grep"]
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

        raise ValueError(f"Unsupported CLI for CriticAgent: {self.cli!r}")

    def parse_output(self, raw: str) -> AgentResponse:
        if self.cli == "claude":
            return parse_claude_json(raw)
        if self.cli == "codex":
            return parse_codex_jsonl(raw)
        if self.cli == "gemini":
            return parse_gemini_json(raw)
        return AgentResponse(text=raw)
