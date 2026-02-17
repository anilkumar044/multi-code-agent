"""agents/parsers.py — CLI-specific output parsers."""
import json
from .base_agent import AgentResponse, TokenLimitError, EmptyResponseError


def parse_claude_json(raw: str) -> AgentResponse:
    try:
        data = json.loads(raw.strip())
        subtype = data.get("subtype", "")
        is_error = data.get("is_error", False)
        text = data.get("result", "")
        session_id = data.get("session_id", "")
        if subtype == "error_max_tokens":
            raise TokenLimitError(f"Claude token limit: {text[:200]}")
        if is_error:
            # Other errors (not token limit) — surface as EmptyResponseError
            raise EmptyResponseError(f"Claude error ({subtype}): {text[:200]}")
        return AgentResponse(text=text, session_id=session_id)
    except (json.JSONDecodeError, KeyError):
        return AgentResponse(text=raw)  # graceful fallback to raw text


def parse_codex_jsonl(raw: str) -> AgentResponse:
    thread_id = ""
    text_parts: list[str] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        etype = event.get("type", "")
        if etype == "thread.started":
            thread_id = event.get("thread_id", "")
        elif etype == "item.completed":
            item = event.get("item", {})
            if item.get("type") == "agent_message":
                text_parts.append(item.get("text", ""))
        elif "error" in etype.lower():
            msg = str(event)
            if any(t in msg.lower() for t in ("context_length", "token", "rate_limit", "too many")):
                raise TokenLimitError(f"Codex limit: {msg[:200]}")
    text = "\n".join(text_parts).strip()
    if not text:
        raise EmptyResponseError(f"Codex returned no agent_message. Raw: {raw[:300]!r}")
    return AgentResponse(text=text, session_id=thread_id)


def parse_gemini_json(raw: str) -> AgentResponse:
    # stdout should be clean JSON; handle any unexpected preamble
    start = raw.find("{")
    if start > 0:
        raw = raw[start:]
    try:
        data = json.loads(raw)
        return AgentResponse(text=data.get("response", raw),
                             session_id=data.get("session_id", ""))
    except json.JSONDecodeError:
        return AgentResponse(text=raw)
