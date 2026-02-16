"""
core/session.py

Session data model — stores all state across iterations and handles JSON persistence.

Schema:
{
  "id":           "session_20260216_143022",
  "task":         "write a binary search",
  "started_at":   "2026-02-16T14:30:22",
  "completed_at": "2026-02-16T14:35:10",
  "config": {"creator": "claude", "reviewer": "codex", "critic": "gemini", "iterations": 3},
  "initial_code":  "...",
  "final_code":    "...",
  "iterations": [
    {"number": 1, "review": "...", "critique": "...", "revision": "..."},
    ...
  ]
}
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional

SESSIONS_DIR = Path(__file__).resolve().parent.parent / "sessions"


@dataclass
class IterationRecord:
    number: int
    review: str = ""
    critique: str = ""
    revision: str = ""


@dataclass
class SessionConfig:
    creator: str
    reviewer: str
    critic: str
    iterations: int


@dataclass
class Session:
    task: str
    config: SessionConfig
    id: str = field(default_factory=lambda: f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    initial_code: str = ""
    final_code: str = ""
    workspace_path: str = ""
    iterations: list = field(default_factory=list)  # list[IterationRecord]

    # ------------------------------------------------------------------ #
    # Mutators — called by the orchestrator as events occur
    # ------------------------------------------------------------------ #

    def set_initial_code(self, code: str) -> None:
        self.initial_code = code
        self.final_code = code

    def start_iteration(self, number: int) -> IterationRecord:
        record = IterationRecord(number=number)
        self.iterations.append(record)
        return record

    def set_review(self, iteration: int, review: str) -> None:
        self.iterations[iteration - 1].review = review

    def set_critique(self, iteration: int, critique: str) -> None:
        self.iterations[iteration - 1].critique = critique

    def set_revision(self, iteration: int, revision: str) -> None:
        self.iterations[iteration - 1].revision = revision
        self.final_code = revision

    def complete(self) -> None:
        self.completed_at = datetime.now().isoformat()

    # ------------------------------------------------------------------ #
    # State accessors — used by Orchestrator to build prompts
    # ------------------------------------------------------------------ #

    @property
    def current_code(self) -> str:
        """The most recent code (latest revision or initial code)."""
        if self.iterations and self.iterations[-1].revision:
            return self.iterations[-1].revision
        return self.initial_code

    @property
    def previous_review(self) -> Optional[str]:
        """Review from the previous iteration (for reviewer update prompt)."""
        if len(self.iterations) >= 2:
            return self.iterations[-2].review
        return None

    @property
    def current_review(self) -> Optional[str]:
        """Review from the current (latest) iteration."""
        if self.iterations and self.iterations[-1].review:
            return self.iterations[-1].review
        return None

    @property
    def current_critique(self) -> Optional[str]:
        """Critique from the previous iteration (for reviewer update context)."""
        # When building reviewer_update, we need the critique from the PRIOR iteration
        if len(self.iterations) >= 2:
            return self.iterations[-2].critique
        return None

    # ------------------------------------------------------------------ #
    # Persistence
    # ------------------------------------------------------------------ #

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "task": self.task,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "config": {
                "creator": self.config.creator,
                "reviewer": self.config.reviewer,
                "critic": self.config.critic,
                "iterations": self.config.iterations,
            },
            "workspace_path": self.workspace_path,
            "initial_code": self.initial_code,
            "final_code": self.final_code,
            "iterations": [
                {
                    "number": it.number,
                    "review": it.review,
                    "critique": it.critique,
                    "revision": it.revision,
                }
                for it in self.iterations
            ],
        }

    def save(self) -> Path:
        """Write session JSON to ./sessions/<id>.json."""
        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)
        path = SESSIONS_DIR / f"{self.id}.json"
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")
        return path
