"""
core/availability.py

Verify that required CLI tools exist in PATH before starting the session.
"""

import shutil

_TOOL_INFO = {
    "claude": {
        "name": "Claude Code CLI",
        "install": "npm install -g @anthropic-ai/claude-code",
    },
    "codex": {
        "name": "OpenAI Codex CLI",
        "install": "npm install -g @openai/codex",
    },
    "gemini": {
        "name": "Google Gemini CLI",
        "install": "npm install -g @google/gemini-cli",
    },
}


class AvailabilityError(Exception):
    pass


def verify_all_tools(required: set, display) -> None:
    """
    Check each binary in `required` is findable via shutil.which().
    Prints a status line per tool and raises AvailabilityError if any are missing.
    """
    missing = []

    display.section("Checking CLI tool availability")
    for binary in sorted(required):
        info = _TOOL_INFO.get(binary, {"name": binary, "install": "see tool documentation"})
        path = shutil.which(binary)
        if path:
            display.tool_found(info["name"], binary, path)
        else:
            display.tool_missing(info["name"], binary, info["install"])
            missing.append(binary)

    display.blank()

    if missing:
        names = ", ".join(missing)
        raise AvailabilityError(
            f"The following CLI tools are not available in PATH: {names}\n"
            "Please install them and ensure they are authenticated before running again."
        )
