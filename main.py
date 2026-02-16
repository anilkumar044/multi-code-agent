"""
main.py

Entry point for the multi-agent coding system.

Usage:
    python main.py "write a binary search"
    python main.py "implement an LRU cache" --creator claude --reviewer openai --critic gemini
    python main.py "write merge sort" --iterations 3 --output sort.py
    python main.py --help
"""

import argparse
import sys
from pathlib import Path

from agents import create_agents, TOOL_MAP
from core.availability import verify_all_tools, AvailabilityError
from core.orchestrator import Orchestrator, OrchestratorError
from display.console import ConsoleDisplay


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="multi-code-agent",
        description="Multi-agent coding system: Creator builds, Reviewer critiques, Critic challenges.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py "write a binary search function"
  python main.py "implement quicksort" --iterations 2 --output quicksort.py
  python main.py "build a rate limiter" --creator gemini --reviewer claude --critic openai
        """,
    )
    parser.add_argument("task", help='The coding task to solve, e.g. "write a binary search"')
    parser.add_argument(
        "--creator",
        choices=["claude", "openai", "gemini"],
        default="claude",
        metavar="AGENT",
        help="Agent to create and revise code (claude|openai|gemini, default: claude)",
    )
    parser.add_argument(
        "--reviewer",
        choices=["claude", "openai", "gemini"],
        default="openai",
        metavar="AGENT",
        help="Agent to review code (claude|openai|gemini, default: openai)",
    )
    parser.add_argument(
        "--critic",
        choices=["claude", "openai", "gemini"],
        default="gemini",
        metavar="AGENT",
        help="Agent to critique the review (claude|openai|gemini, default: gemini)",
    )
    parser.add_argument(
        "--iterations",
        "-n",
        type=int,
        default=5,
        metavar="N",
        help="Number of review → critique → revise cycles (default: 5)",
    )
    parser.add_argument(
        "--output",
        "-o",
        metavar="FILE",
        help="Write final code to this file (e.g. solution.py)",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=120,
        metavar="SECONDS",
        help="Per-agent call timeout in seconds (default: 120)",
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Do not save the session transcript to ./sessions/",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    display = ConsoleDisplay()

    # Determine the set of CLI binaries needed (may be fewer than 3 if roles share an agent)
    required_binaries = {TOOL_MAP[args.creator], TOOL_MAP[args.reviewer], TOOL_MAP[args.critic]}

    # Check all required tools are installed
    try:
        verify_all_tools(required_binaries, display)
    except AvailabilityError as exc:
        display.error(str(exc))
        sys.exit(1)

    # Instantiate agents
    creator, reviewer, critic = create_agents(
        creator_key=args.creator,
        reviewer_key=args.reviewer,
        critic_key=args.critic,
        timeout=args.timeout,
        display=display,
    )

    # Run the orchestrated loop
    try:
        orchestrator = Orchestrator(
            creator=creator,
            reviewer=reviewer,
            critic=critic,
            iterations=args.iterations,
            display=display,
        )
        session = orchestrator.run(task=args.task)
    except OrchestratorError as exc:
        display.error(f"Orchestration failed: {exc}")
        sys.exit(1)

    # Show final code
    display.done(session.final_code)

    # Optionally write final code to file
    if args.output:
        output_path = Path(args.output)
        output_path.write_text(session.final_code, encoding="utf-8")
        display.success(f"Final code written to: {output_path.resolve()}")

    # Print workspace path so user can inspect generated files
    if session.workspace_path:
        display.success(f"Workspace files: {session.workspace_path}")

    # Save session transcript
    if not args.no_save:
        saved_path = session.save()
        display.success(f"Session saved to: {saved_path}")


if __name__ == "__main__":
    main()
