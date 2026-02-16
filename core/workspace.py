"""
core/workspace.py

Manages the shared filesystem workspace for a session.
All agents read from and write to sessions/<session_id>/workspace/.
"""

import shutil
import subprocess
from pathlib import Path

SESSIONS_DIR = Path(__file__).resolve().parent.parent / "sessions"


class Workspace:
    """
    Per-session workspace directory.

    Fixed files:
      workspace/solution.py   — the current solution
      workspace/tests.py      — pytest test suite
      workspace/test_results.txt — output from last test run

    Per-cycle files (under workspace/reviews/):
      reviews/review_{n}.md
      reviews/critique_{n}.md

    Snapshots (under workspace/snapshots/):
      snapshots/v{n}.py
    """

    def __init__(self, session_id: str) -> None:
        self.session_id = session_id
        self.path: Path = SESSIONS_DIR / session_id / "workspace"
        self.path.mkdir(parents=True, exist_ok=True)
        (self.path / "reviews").mkdir(exist_ok=True)
        (self.path / "snapshots").mkdir(exist_ok=True)

    # ------------------------------------------------------------------ #
    # Fixed file paths
    # ------------------------------------------------------------------ #

    @property
    def solution_path(self) -> Path:
        return self.path / "solution.py"

    @property
    def tests_path(self) -> Path:
        return self.path / "tests.py"

    def review_path(self, cycle: int) -> Path:
        return self.path / "reviews" / f"review_{cycle}.md"

    def critique_path(self, cycle: int) -> Path:
        return self.path / "reviews" / f"critique_{cycle}.md"

    # ------------------------------------------------------------------ #
    # Safe readers — return "" if file missing
    # ------------------------------------------------------------------ #

    def read_solution(self) -> str:
        return self.solution_path.read_text(encoding="utf-8") if self.solution_path.exists() else ""

    def read_tests(self) -> str:
        return self.tests_path.read_text(encoding="utf-8") if self.tests_path.exists() else ""

    def read_review(self, cycle: int) -> str:
        p = self.review_path(cycle)
        return p.read_text(encoding="utf-8") if p.exists() else ""

    def read_critique(self, cycle: int) -> str:
        p = self.critique_path(cycle)
        return p.read_text(encoding="utf-8") if p.exists() else ""

    # ------------------------------------------------------------------ #
    # Writers
    # ------------------------------------------------------------------ #

    def write_critique(self, cycle: int, text: str) -> None:
        self.critique_path(cycle).write_text(text, encoding="utf-8")

    # ------------------------------------------------------------------ #
    # Test runner
    # ------------------------------------------------------------------ #

    def run_tests(self) -> str:
        """
        Run pytest on tests.py in the workspace directory.
        Returns combined stdout+stderr output.
        Returns a message if tests.py doesn't exist.
        """
        if not self.tests_path.exists():
            return "(no tests.py found in workspace)"

        try:
            result = subprocess.run(
                ["python", "-m", "pytest", "tests.py", "-v", "--tb=short"],
                cwd=str(self.path),
                capture_output=True,
                text=True,
                timeout=120,
            )
            output = result.stdout
            if result.stderr:
                output += "\n" + result.stderr
            return output.strip()
        except FileNotFoundError:
            return "(python not found — cannot run tests)"
        except subprocess.TimeoutExpired:
            return "(test run timed out after 120s)"

    # ------------------------------------------------------------------ #
    # Snapshot
    # ------------------------------------------------------------------ #

    def snapshot(self, cycle: int) -> None:
        """Copy current solution.py to snapshots/v{cycle}.py before revision."""
        if self.solution_path.exists():
            dest = self.path / "snapshots" / f"v{cycle}.py"
            shutil.copy2(self.solution_path, dest)

    # ------------------------------------------------------------------ #
    # Manifest
    # ------------------------------------------------------------------ #

    def manifest(self) -> str:
        """Return a text listing of all files in the workspace (for prompts)."""
        lines = []
        for p in sorted(self.path.rglob("*")):
            if p.is_file():
                rel = p.relative_to(self.path)
                lines.append(f"  {rel}")
        if not lines:
            return "  (workspace is empty)"
        return "\n".join(lines)
