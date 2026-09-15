"""Usage and quota limits slash command handler."""

from rich.panel import Panel
from rich.table import Table
from rich import box
from cli.config import console
from cli.core.client import APIClient
from cli.ui.banners import get_terminal_width


def handle_usage() -> None:
    """Fetches and displays current plan usage limits and reset dates."""
    console.print("\n[dim]Fetching Gemini account usage quotas...[/dim]")
    try:
        data = APIClient.fetch_usage()
        term_width = get_terminal_width()

        bar_total_len = max(8, min(24, term_width - 55))

        table = Table(show_header=True, header_style="bold yellow", box=box.SIMPLE_HEAD, expand=True)
        table.add_column("Quota Window", style="bold white", width=18)
        table.add_column("Consumption", style="bold cyan", width=16)
        table.add_column("Progress Bar", width=bar_total_len + 4)
        table.add_column("Reset Schedule", style="green")

        def make_bar(percent: float) -> str:
            filled_count = int((percent / 100.0) * bar_total_len)
            filled_count = min(bar_total_len, max(0, filled_count))
            filled = "█" * filled_count
            empty = "░" * (bar_total_len - filled_count)
            color = "green" if percent < 70 else ("yellow" if percent < 90 else "red")
            return f"[{color}]{filled}{empty}[/{color}]"

        curr_p = data.get("current_percent", 0.0)
        curr_txt = data.get("current_usage", f"{curr_p}% used")
        curr_reset = data.get("current_reset_time", "Unknown")
        table.add_row("Current Limit", curr_txt, make_bar(curr_p), curr_reset)

        week_p = data.get("weekly_percent", 0.0)
        week_txt = data.get("weekly_usage", f"{week_p}% used")
        week_reset = data.get("weekly_reset_time", "Unknown")
        table.add_row("Weekly Limit", week_txt, make_bar(week_p), week_reset)

        tier = data.get("tier", "PRO")
        panel = Panel(
            table,
            title=f"[bold yellow]Gemini Plan Usage Limits [{tier}][/bold yellow]",
            subtitle="[dim]Live metrics retrieved from gemini.google.com/usage[/dim]",
            border_style="yellow",
            box=box.ROUNDED,
            padding=(1, 2),
            expand=True,
        )
        console.print()
        console.print(panel)
        console.print()

    except Exception as exc:
        console.print(f"[red]Error fetching usage metrics:[/red] {exc}\n")

