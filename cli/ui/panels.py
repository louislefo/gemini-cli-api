"""Panel presentation components for responses and status notifications."""

from rich.markdown import Markdown
from rich.panel import Panel
from rich.text import Text
from rich import box
from cli.config import console


def render_response_panel(response_text: str, duration: float) -> None:
    """Renders formatted Markdown response panel."""
    console.print(
        Panel(
            Markdown(response_text, code_theme="monokai"),
            border_style="bright_blue",
            box=box.ROUNDED,
            padding=(1, 2),
            expand=True,
            title="[bold green]Structured Response[/bold green]",
            subtitle=f"[bold cyan]{round(duration, 2)}s[/bold cyan] [dim]|[/dim] [dim]{len(response_text)} characters[/dim]",
            subtitle_align="right",
        )
    )
    console.print()


def render_error_panel(error_text: str) -> None:
    """Renders an error panel."""
    console.print(
        Panel(
            Text(error_text, style="bold red"),
            border_style="red",
            box=box.ROUNDED,
            padding=(1, 2),
            expand=True,
        )
    )
    console.print()


import time
from rich.console import Group
from rich.table import Table


def render_exit_panel(stats_obj=None) -> None:
    """Renders a polished, comprehensive goodbye exit panel with session metrics."""
    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="bold cyan", width=28)
    table.add_column("Value", style="white")

    if stats_obj:
        elapsed = round(time.time() - getattr(stats_obj, "start_time", time.time()), 1)
        total_prompts = getattr(stats_obj, "total_prompts", 0)
        total_chars = getattr(stats_obj, "total_chars_received", 0)
        total_gen = getattr(stats_obj, "total_generation_time", 0.0)

        table.add_row("Session Duration", f"{elapsed}s")
        table.add_row("Total Prompts Sent", str(total_prompts))
        table.add_row("Total Characters Received", f"{total_chars:,}")
        if total_prompts > 0:
            avg_time = round(total_gen / total_prompts, 2)
            table.add_row("Average Response Latency", f"{avg_time}s")

    table.add_row("Gemini Profile Session", "[bold green]Persisted & Safe[/bold green]")
    table.add_row("Resume / Relaunch", "[dim]Run [bold white]python run.py[/bold white] or [bold white]gemini-cli-api[/bold white][/dim]")

    exit_intro = Text()
    exit_intro.append("Session Terminated Gracefully\n\n", style="bold white")
    exit_intro.append("Your Chrome profile, conversation history, and authentication state are preserved.\n", style="dim")

    panel_content = Group(
        exit_intro,
        table,
    )

    console.print()
    console.print(
        Panel(
            panel_content,
            title="[bold cyan]GEMINI-CLI-API Exit[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED,
            padding=(1, 2),
            expand=True,
        )
    )
    console.print()

