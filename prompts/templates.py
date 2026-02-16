"""
prompts/templates.py

All prompt templates for each agent role × phase.

Roles:   Creator, Reviewer, Critic
Phases:
  Creator:  initial, revision (iteration 2+)
  Reviewer: initial (iteration 1), update (iteration 2+)
  Critic:   single phase (challenges the review)

Workspace-aware design: agents operate in a shared filesystem workspace.
- Creator writes solution.py, tests.py, runs tests directly.
- Reviewer reads files and runs tests autonomously.
- Critic receives code+review inline (most reliable across CLIs).
"""

from typing import Optional


class PromptBuilder:
    """Builds prompts for each agent role and phase."""

    # ------------------------------------------------------------------ #
    # CREATOR — Initial
    # ------------------------------------------------------------------ #

    def creator_initial(self, task: str) -> str:
        return f"""You are an expert software engineer. Your job is to implement a solution and tests for the following task.

TASK: {task}

WORKSPACE INSTRUCTIONS:
You are operating in a shared workspace directory. Perform these steps in order:

1. Write your complete solution to `solution.py`
   - Production-quality Python code
   - Docstrings and inline comments for non-obvious logic
   - Proper error handling
   - A usage example in a `if __name__ == "__main__"` guard

2. Write a comprehensive pytest test suite to `tests.py`
   - Cover normal cases, edge cases, and error cases
   - Use descriptive test function names (test_<what>_<scenario>)
   - Import from solution (e.g. `from solution import MyClass`)

3. Run the tests and fix any failures:
   ```
   python -m pytest tests.py -v 2>&1 | tee test_results.txt
   ```
   If tests fail, revise `solution.py` and re-run until all tests pass.

4. Do not print the code to stdout — write it to the files above.

COMPLEXITY NOTE: If this task has independent components (e.g. separate modules, a core class + utilities + tests), consider using the Task tool to develop them in parallel for speed.
"""

    # ------------------------------------------------------------------ #
    # CREATOR — Revision
    # ------------------------------------------------------------------ #

    def creator_revision(self, task: str, cycle: int) -> str:
        return f"""You are an expert software engineer revising Python code based on structured feedback.

ORIGINAL TASK: {task}

WORKSPACE INSTRUCTIONS (revision cycle {cycle}):
You are operating in a shared workspace directory. Perform these steps in order:

1. Read the current state:
   - `solution.py` — the code to revise
   - `tests.py` — the test suite
   - `reviews/review_{cycle}.md` — the reviewer's feedback
   - `reviews/critique_{cycle}.md` — the critic's perspective on the review

2. Apply revisions to `solution.py`:
   - Fix real bugs and security issues identified in the review
     (unless the critic convincingly argues they are false positives)
   - Apply performance improvements where practical
   - Ignore review points the critic identifies as false positives
   - Do NOT regress: keep all working functionality

3. Update `tests.py` if needed (e.g. to cover newly fixed edge cases).

4. Run the tests and fix any regressions:
   ```
   python -m pytest tests.py -v 2>&1 | tee test_results.txt
   ```
   If tests fail, fix `solution.py` and re-run until all pass.

5. Write a brief summary of what you changed to stdout (a few bullet points).
"""

    # ------------------------------------------------------------------ #
    # REVIEWER — Initial (cycle 1)
    # ------------------------------------------------------------------ #

    def reviewer_initial(self, task: str, manifest: str) -> str:
        return f"""You are a senior software engineer performing a code review.

TASK CONTEXT: The code was written to solve: {task}

WORKSPACE FILES:
{manifest}

INSTRUCTIONS:
1. Read `solution.py` and `tests.py` from the workspace.

2. Run the test suite to verify correctness:
   ```
   python -m pytest tests.py -v --tb=long 2>&1 | tee test_run_reviewer.txt
   ```

3. Write a structured review to `reviews/review_1.md` covering:

   ## 1. TEST RESULTS
   Paste the test run summary (pass/fail counts, any failures).

   ## 2. BUGS & CORRECTNESS
   Logic errors, off-by-one errors, incorrect assumptions, missing null/empty checks,
   cases where the code doesn't actually solve the task.

   ## 3. SECURITY
   Input validation gaps, injection vulnerabilities, unsafe eval/exec usage, credential exposure.

   ## 4. PERFORMANCE
   Inefficient algorithms (note current vs. optimal complexity), unnecessary memory allocation,
   repeated computation, missing early-exit opportunities.

   ## 5. CODE QUALITY
   Unclear naming, missing or inadequate docstrings, dead code, redundant logic,
   violations of Python idioms (PEP 8, comprehensions, etc.).

   ## 6. OVERALL VERDICT
   Rate the code: POOR / FAIR / GOOD / EXCELLENT
   List the top 3 issues that MUST be fixed vs. nice-to-have improvements.

Be objective. If the code is genuinely good, say so. Do not invent problems.
"""

    # ------------------------------------------------------------------ #
    # REVIEWER — Update (cycle 2+)
    # ------------------------------------------------------------------ #

    def reviewer_update(self, task: str, manifest: str, cycle: int) -> str:
        prior = cycle - 1
        return f"""You are a senior software engineer performing an updated code review.

TASK CONTEXT: {task}

The code has been revised based on feedback from cycle {prior}. A critic also evaluated your last review.

WORKSPACE FILES:
{manifest}

INSTRUCTIONS:
1. Read the revised `solution.py` and `tests.py`.

2. Read your previous review at `reviews/review_{prior}.md` and the critic's evaluation at `reviews/critique_{prior}.md`.

3. Run the test suite:
   ```
   python -m pytest tests.py -v --tb=long 2>&1 | tee test_run_reviewer.txt
   ```

4. Write your updated review to `reviews/review_{cycle}.md` with this structure:

   ## 1. TEST RESULTS
   Paste the test run summary.

   ## 2. CHANGES SINCE LAST REVIEW
   - Issues resolved: (list what was fixed)
   - Issues NOT addressed: (still present from prior review)
   - New issues introduced by the revision

   ## 3. BUGS & CORRECTNESS (Updated)
   ## 4. SECURITY (Updated)
   ## 5. PERFORMANCE (Updated)
   ## 6. CODE QUALITY (Updated)

   ## 7. OVERALL VERDICT (Updated)
   - Reconsider items the critic flagged as false positives — acknowledge or rebut
   - Rating: POOR / FAIR / GOOD / EXCELLENT
   - Remaining MUST-FIX issues
"""

    # ------------------------------------------------------------------ #
    # CRITIC — Single phase
    # ------------------------------------------------------------------ #

    def critic(
        self,
        task: str,
        solution_code: str,
        review_text: str,
        cycle: int,
        prior_critique: Optional[str] = None,
    ) -> str:
        prior_section = ""
        if prior_critique:
            prior_section = f"""
YOUR PREVIOUS CRITIQUE (cycle {cycle - 1}):
{prior_critique}

Consider whether the issues you raised previously were addressed in the revised code.

"""
        return f"""You are a principal engineer acting as a critical second opinion on a code review.

TASK CONTEXT: The code was written to solve: {task}
{prior_section}
THE CODE THAT WAS REVIEWED (solution.py):
```python
{solution_code}
```

THE REVIEW YOU ARE EVALUATING (reviews/review_{cycle}.md):
{review_text}

Your job is NOT to re-review the code. Your job is to critically evaluate the REVIEW ITSELF.

## 1. MISSED ISSUES
What real problems exist in the code that the reviewer failed to mention?
Analyze the code yourself to find gaps — do not just repeat what the reviewer said.

## 2. FALSE POSITIVES
Which review points are incorrect, overstated, or not actually problems for this task/context?
Explain WHY each is a false positive.

## 3. PRIORITY CALIBRATION
Are the reviewer's priorities correct?
- Are any "must fix" items actually minor or cosmetic?
- Are any "nice to have" items actually critical?
- Is the overall verdict (rating) fair?

## 4. BALANCE ASSESSMENT
Is the review appropriately balanced — too harsh, too lenient, or about right?

## 5. ACTIONABLE RECOMMENDATIONS
What should the Creator ACTUALLY focus on when revising?
List at most 5 concrete, ranked action items — synthesizing both the review's valid points and your own findings.

Be direct and honest. A good critic improves the quality of the feedback loop.
"""
