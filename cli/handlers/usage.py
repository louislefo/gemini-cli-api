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


def handle_account() -> None:
    """Fetches and displays connected Google account details and subscription tier."""
    console.print("\n[dim]Fetching connected Google Account details...[/dim]")
    try:
        acc = APIClient.fetch_account()
        email = acc.get("email", "Unknown")
        name = acc.get("name", "Unknown")
        tier = acc.get("tier", "Free (Standard)")
        authenticated = acc.get("authenticated", False)

        table = Table(show_header=False, box=box.SIMPLE, expand=True)
        table.add_column("Property", style="bold cyan", width=24)
        table.add_column("Value", style="bold white")

        table.add_row("Google Account", email if email != "Unknown" else "[dim]Not detected[/dim]")
        table.add_row("Display Name", name if name != "Unknown" else "[dim]Not detected[/dim]")

        tier_style = "bold magenta" if ("pro" in tier.lower() or "advanced" in tier.lower()) else "bold green"
        table.add_row("Plan Tier", f"[{tier_style}]{tier}[/{tier_style}]")
        table.add_row("Auth Status", "[bold green]Active & Authenticated[/bold green]" if authenticated else "[yellow]Unauthenticated[/yellow]")

        panel = Panel(
            table,
            title="[bold cyan]Connected Google Account[/bold cyan]",
            subtitle="[dim]Type /switch-account to log in with a different Google account[/dim]",
            border_style="cyan",
            box=box.ROUNDED,
            padding=(1, 2),
            expand=True,
        )
        console.print()
        console.print(panel)
        console.print()

    except Exception as exc:
        console.print(f"[red]Error fetching account details:[/red] {exc}\n")


def handle_switch_account() -> None:
    """Initiates account logout and interactive sign-in flow for a new Google account."""
    import asyncio
    import os
    import shutil
    import time
    from auth import (
        DEFAULT_CDP_PORT,
        DEFAULT_PROFILE_DIR,
        find_chrome_executable,
        launch_chrome_process,
        run_login_flow,
        stop_chrome,
    )

    console.print("\n[bold yellow]Switching Google Account...[/bold yellow]")
    console.print("[dim]1. Terminating background headless Chrome session...[/dim]")
    stop_chrome(DEFAULT_CDP_PORT)
    time.sleep(1.0)

    profile_dir = os.path.abspath(DEFAULT_PROFILE_DIR)
    if os.path.exists(profile_dir):
        try:
            shutil.rmtree(profile_dir)
        except Exception:
            shutil.rmtree(profile_dir, ignore_errors=True)
    console.print("[dim]2. Resetting local profile session...[/dim]")

    chrome_path = find_chrome_executable()
    if not chrome_path:
        console.print("[bold red]Google Chrome executable not found.[/bold red]\n")
        return

    login_ok = asyncio.run(run_login_flow(chrome_path, profile_dir, DEFAULT_CDP_PORT))
    if login_ok:
        console.print("[bold cyan]Relaunching background headless Chrome engine...[/bold cyan]")
        launch_chrome_process(
            chrome_path=chrome_path,
            profile_dir=profile_dir,
            port=DEFAULT_CDP_PORT,
            headless=True,
            url="https://gemini.google.com/app",
        )
        time.sleep(1.5)
        console.print("[bold green]Account switched successfully! You can now send prompts.[/bold green]\n")
    else:
        console.print("[bold red]Account switch cancelled or timed out.[/bold red]\n")


