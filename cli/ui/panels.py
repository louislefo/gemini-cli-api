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


def render_exit_panel() -> None:
    """Renders goodbye exit panel."""
    console.print(
        Panel(
            Text("Session finished successfully. Goodbye!", style="bold cyan"),
            border_style="cyan",
            box=box.ROUNDED,
            padding=(0, 2),
        )
    )
    console.print()
