"""
core/orchestrator.py

Main feedback loop controller.

Flow:
  Phase 0 — Creator generates initial code, writes solution.py + tests.py, runs tests.
  Loop (N cycles):
    (a) Reviewer reads workspace files, runs tests, writes reviews/review_{i}.md
    (b) Critic    receives code+review inline → returns text → saved to reviews/critique_{i}.md
    (c) Creator   reads review+critique, revises solution.py, re-runs tests
  Returns the final Session with all state recorded.
"""

from agents.base_agent import AgentError
from core.session import Session, SessionConfig
from core.workspace import Workspace
from prompts.templates import PromptBuilder


class OrchestratorError(Exception):
    pass


class Orchestrator:
    def __init__(self, creator, reviewer, critic, iterations: int, display):
        self.creator = creator
        self.reviewer = reviewer
        self.critic = critic
        self.iterations = iterations
        self.display = display
        self.prompts = PromptBuilder()

    def run(self, task: str) -> Session:
        session = Session(
            task=task,
            config=SessionConfig(
                creator=self.creator.cli,
                reviewer=self.reviewer.cli,
                critic=self.critic.cli,
                iterations=self.iterations,
            ),
        )

        # Set up shared workspace
        workspace = Workspace(session.id)
        session.workspace_path = str(workspace.path)

        self.display.header(task, self.iterations)

        # ---------------------------------------------------------------- #
        # Phase 0: Initial code generation
        # ---------------------------------------------------------------- #
        self.display.phase_header("Initial Code Generation", phase=0, total=self.iterations)

        creator_output = self._call(
            self.creator,
            self.prompts.creator_initial(task),
            "Generating initial code...",
            cwd=workspace.path,
        )

        # Prefer the file the agent wrote; fall back to captured stdout
        solution = workspace.read_solution() or creator_output
        session.set_initial_code(solution)

        self.display.agent_output(
            role=self.creator.ROLE,
            color=self.creator.COLOR,
            cli=self.creator.cli,
            content=creator_output,
            is_code=False,
            label="Initial Implementation",
        )

        # Run tests and display results
        test_output = workspace.run_tests()
        if test_output:
            self.display.test_results(test_output)

        # ---------------------------------------------------------------- #
        # Iterative loop
        # ---------------------------------------------------------------- #
        for i in range(1, self.iterations + 1):
            session.start_iteration(i)
            self.display.phase_header(f"Review Cycle {i}", phase=i, total=self.iterations)

            # Snapshot solution before this revision cycle
            workspace.snapshot(i)

            # (a) Reviewer ------------------------------------------------ #
            manifest = workspace.manifest()
            if i == 1:
                review_prompt = self.prompts.reviewer_initial(
                    task=task,
                    manifest=manifest,
                )
            else:
                review_prompt = self.prompts.reviewer_update(
                    task=task,
                    manifest=manifest,
                    cycle=i,
                )

            reviewer_output = self._call(
                self.reviewer,
                review_prompt,
                f"[{i}/{self.iterations}] Reviewing code...",
                cwd=workspace.path,
            )

            # Prefer the file the reviewer wrote; fall back to captured stdout
            review = workspace.read_review(i) or reviewer_output
            session.set_review(i, review)

            self.display.agent_output(
                role=self.reviewer.ROLE,
                color=self.reviewer.COLOR,
                cli=self.reviewer.cli,
                content=review,
                is_code=False,
                label=f"Review (cycle {i})",
            )

            # (b) Critic -------------------------------------------------- #
            solution = workspace.read_solution() or session.current_code
            prior_critique = workspace.read_critique(i - 1) if i > 1 else None

            critique_prompt = self.prompts.critic(
                task=task,
                solution_code=solution,
                review_text=review,
                cycle=i,
                prior_critique=prior_critique,
            )
            critique = self._call(
                self.critic,
                critique_prompt,
                f"[{i}/{self.iterations}] Critiquing the review...",
                cwd=workspace.path,
            )

            # Critic returns text — save it to file for future agents to read
            workspace.write_critique(i, critique)
            session.set_critique(i, critique)

            self.display.agent_output(
                role=self.critic.ROLE,
                color=self.critic.COLOR,
                cli=self.critic.cli,
                content=critique,
                is_code=False,
                label=f"Challenge (cycle {i})",
            )

            # (c) Creator revision ---------------------------------------- #
            revision_output = self._call(
                self.creator,
                self.prompts.creator_revision(task=task, cycle=i),
                f"[{i}/{self.iterations}] Revising code...",
                cwd=workspace.path,
            )

            # Prefer file; fall back to stdout
            revision = workspace.read_solution() or revision_output
            session.set_revision(i, revision)

            self.display.agent_output(
                role=self.creator.ROLE,
                color=self.creator.COLOR,
                cli=self.creator.cli,
                content=revision_output,
                is_code=False,
                label=f"Revision (cycle {i})",
            )

            # Run tests after each revision
            test_output = workspace.run_tests()
            if test_output:
                self.display.test_results(test_output)

        session.complete()
        return session

    def _call(self, agent, prompt: str, spinner_text: str, cwd=None) -> str:
        """Run an agent call with a spinner and unified error handling."""
        try:
            with self.display.spinner(spinner_text, color=agent.COLOR):
                return agent.run(prompt, cwd=cwd)
        except AgentError as exc:
            self.display.agent_error(agent.ROLE, agent.cli, str(exc))
            raise OrchestratorError(f"{agent.ROLE} failed: {exc}") from exc
