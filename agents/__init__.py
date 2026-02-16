from .creator_agent import CreatorAgent
from .reviewer_agent import ReviewerAgent
from .critic_agent import CriticAgent
from .base_agent import BaseAgent, AgentError, AgentTimeoutError, CLINotFoundError, EmptyResponseError

TOOL_MAP = {
    "claude": "claude",
    "openai": "codex",
    "gemini": "gemini",
}


def create_agents(creator_key: str, reviewer_key: str, critic_key: str, timeout: int, display):
    """Instantiate the three role agents from user-facing key names (claude/openai/gemini)."""
    return (
        CreatorAgent(cli=TOOL_MAP[creator_key],  timeout=timeout, display=display),
        ReviewerAgent(cli=TOOL_MAP[reviewer_key], timeout=timeout, display=display),
        CriticAgent(cli=TOOL_MAP[critic_key],    timeout=timeout, display=display),
    )
