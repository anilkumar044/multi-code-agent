"""
display/console.py

Rich-based display layer. All visual output is routed through ConsoleDisplay.

Color conventions:
  cyan    = Creator  (Claude by default)
  green   = Reviewer (Codex by default)
  magenta = Critic   (Gemini by default)
  yellow  = System / headers
  red     = Errors
"""

from contextlib import contextmanager

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.rule import Rule
from rich.spinner import Spinner
from rich.syntax import Syntax
from rich.text import Text

_console = Console()

_CLI_LABELS = {
    "claude": "Claude",
    "codex": "Codex",
    "gemini": "Gemini",
}


class ConsoleDisplay:
    """Centralised display for all console output."""

    # ------------------------------------------------------------------ #
    # Structural elements
    # ------------------------------------------------------------------ #

    def header(self, task: str, iterations: int) -> None:
        _console.print()
        _console.print(
            Panel(
                f"[bold white]Multi-Agent Code Generator[/bold white]\n"
                f'[dim]Task:[/dim] [yellow]{task}[/yellow]   '
                f'[dim]Iterations:[/dim] [yellow]{iterations}[/yellow]',
                border_style="bold blue",
                padding=(1, 2),
            )
        )
        _console.print()

    def phase_header(self, label: str, phase: int, total: int) -> None:
        if phase == 0:
            _console.print(Rule(f"  Phase 0 — {label}  ", style="yellow"))
        else:
            _console.print(Rule(f"  Cycle {phase}/{total} — {label}  ", style="yellow"))
        _console.print()

    def section(self, label: str) -> None:
        _console.print(Rule(f" {label} ", style="dim"))

    def blank(self) -> None:
        _console.print()

    # ------------------------------------------------------------------ #
    # Agent output panels
    # ------------------------------------------------------------------ #

    def agent_output(
        self,
        role: str,
        color: str,
        cli: str,
        content: str,
        is_code: bool,
        label: str = "",
    ) -> None:
        display_name = _CLI_LABELS.get(cli, cli)
        title = f" {role} ({display_name})"
        if label:
            title += f" — {label}"
        title += " "

        if is_code:
            renderable = Syntax(
                content,
                "python",
                theme="monokai",
                line_numbers=True,
                word_wrap=True,
            )
        else:
            renderable = Text(content, overflow="fold")

        _console.print(
            Panel(
                renderable,
                title=title,
                title_align="left",
                border_style=color,
                padding=(1, 2),
            )
        )
        _console.print()

    def agent_error(self, role: str, cli: str, message: str) -> None:
        display_name = _CLI_LABELS.get(cli, cli)
        _console.print(
            Panel(
                Text(message, style="red"),
                title=f" Error — {role} ({display_name}) ",
                title_align="left",
                border_style="red",
                padding=(1, 2),
            )
        )

    # ------------------------------------------------------------------ #
    # Availability check output
    # ------------------------------------------------------------------ #

    def tool_found(self, name: str, binary: str, path: str) -> None:
        _console.print(
            f"  [bold green]FOUND[/bold green]   {name} "
            f"([cyan]{binary}[/cyan])  [dim]{path}[/dim]"
        )

    def tool_missing(self, name: str, binary: str, install_hint: str) -> None:
        _console.print(
            f"  [bold red]MISSING[/bold red]  {name} ([cyan]{binary}[/cyan])\n"
            f"            Install: [dim]{install_hint}[/dim]"
        )

    # ------------------------------------------------------------------ #
    # Spinner context manager
    # ------------------------------------------------------------------ #

    @contextmanager
    def spinner(self, text: str, color: str = "white"):
        """Display a spinner while a block executes."""
        spinner_obj = Spinner("dots", text=f"[{color}]{text}[/{color}]")
        with Live(spinner_obj, console=_console, refresh_per_second=10, transient=True):
            yield

    # ------------------------------------------------------------------ #
    # Terminal messages
    # ------------------------------------------------------------------ #

    def error(self, message: str) -> None:
        _console.print(f"\n[bold red]Error:[/bold red] {message}\n")

    def success(self, message: str) -> None:
        _console.print(f"[bold green]✓[/bold green] {message}")

    def test_results(self, output: str) -> None:
        """Display pytest output in a yellow panel with pass/fail highlighting."""
        lines = output.splitlines()
        text = Text()
        for line in lines:
            line_lower = line.lower()
            if "failed" in line_lower or "error" in line_lower:
                text.append(line + "\n", style="bold red")
            elif "passed" in line_lower or "passed" in line_lower:
                text.append(line + "\n", style="bold green")
            elif line.startswith("PASSED") or " PASSED" in line:
                text.append(line + "\n", style="dim green")
            elif line.startswith("FAILED") or " FAILED" in line:
                text.append(line + "\n", style="red")
            else:
                text.append(line + "\n", style="dim")

        _console.print(
            Panel(
                text,
                title=" Test Results ",
                title_align="left",
                border_style="yellow",
                padding=(0, 2),
            )
        )
        _console.print()

    def done(self, final_code: str) -> None:
        """Print the final code summary panel."""
        _console.print(Rule(" Final Output ", style="bold green"))
        _console.print()
        _console.print(
            Panel(
                Syntax(
                    final_code,
                    "python",
                    theme="monokai",
                    line_numbers=True,
                    word_wrap=True,
                ),
                title=" Final Revised Code ",
                title_align="left",
                border_style="bold green",
                padding=(1, 2),
            )
        )
        _console.print()
