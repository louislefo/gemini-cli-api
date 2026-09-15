"""Table presentation components for help, status, history, and config."""

from rich.panel import Panel
from rich.table import Table
from rich import box
from cli.config import API_BASE_URL, HISTORY_FILE, console
from cli.ui.banners import get_terminal_width


def render_help_table() -> None:
    """Displays the help table with all available slash commands."""
    table = Table(show_header=True, header_style="bold cyan", box=box.SIMPLE_HEAD, expand=True)
    table.add_column("Command", style="bold yellow", width=16)
    table.add_column("Description", style="white")

    table.add_row("/model [name]", "Interactive arrow-key selector or direct model switch (flash, pro, ...)")
    table.add_row("/account", "Show connected Google Account email, name, and plan tier (Pro/Free)")
    table.add_row("/switch-account", "Switch Google Account (log out & open visible sign-in window)")
    table.add_row("/usage", "Display current & weekly quota usage limits and reset times (PRO)")
    table.add_row("/convs", "List previous conversations saved on Gemini")
    table.add_row("/load [id]", "Interactive arrow-key selector or direct resume of a past chat")
    table.add_row("/new [prompt]", "Start a fresh new conversation on Gemini (or send prompt directly)")
    table.add_row("/status", "Check Chrome CDP bridge and Gemini tab connection diagnostic")
    table.add_row("/stream", "Toggle between real-time streaming and standard response mode")
    table.add_row("/save [file]", "Export active conversation history to a Markdown file")
    table.add_row("/stats", "Display session performance and metrics")
    table.add_row("/history", "Show recent prompt history")
    table.add_row("/config", "Show active API configuration")
    table.add_row("/clear", "Clear terminal screen")
    table.add_row("/help", "Show this help menu")
    table.add_row("/exit", "Exit application with session summary")


    panel = Panel(
        table,
        title="[bold cyan]Available Slash Commands[/bold cyan]",
        border_style="cyan",
        box=box.ROUNDED,
        padding=(1, 2),
        expand=True,
    )
    console.print()
    console.print(panel)
    console.print()


def render_status_table(status_data: dict) -> None:
    """Renders connection status diagnostic table."""
    table = Table(show_header=True, header_style="bold blue", box=box.SIMPLE_HEAD, expand=True)
    table.add_column("Component", style="bold white", width=18)
    table.add_column("Status", style="bold", width=16)
    table.add_column("Details", style="dim")

    table.add_row("FastAPI Server", "[green]Online[/green]", API_BASE_URL)
    cdp_status = "[green]Connected[/green]" if status_data.get("connected") else "[red]Disconnected[/red]"
    table.add_row("CDP Port (9222)", cdp_status, status_data.get("cdp_url", ""))

    gemini_status = "[green]Detected[/green]" if status_data.get("gemini_tab_found") else "[yellow]Not Detected[/yellow]"
    page_info = status_data.get("page_title") or status_data.get("url") or "No active tab"
    table.add_row("Gemini Tab", gemini_status, page_info[:80])

    panel = Panel(
        table,
        title="[bold blue]Connection Diagnostic[/bold blue]",
        border_style="blue",
        box=box.ROUNDED,
        padding=(1, 2),
        expand=True,
    )
    console.print()
    console.print(panel)
    console.print()


def render_history_table(history_entries: list[dict]) -> None:
    """Renders recent prompts table."""
    if not history_entries:
        console.print("[dim]No recent prompt history in this session.[/dim]\n")
        return

    term_width = get_terminal_width()
    max_prompt_len = max(20, term_width - 25)

    table = Table(title="Prompt History", show_header=True, expand=True)
    table.add_column("#", width=4)
    table.add_column("Time", width=10)
    table.add_column("Prompt", style="cyan")
    for idx, entry in enumerate(history_entries[-10:], 1):
        prompt_snippet = entry["prompt"][:max_prompt_len] + ("..." if len(entry["prompt"]) > max_prompt_len else "")
        table.add_row(str(idx), entry["timestamp"].split()[1], prompt_snippet)
    console.print()
    console.print(table)
    console.print()


def render_config_table(streaming_mode: bool) -> None:
    """Renders active configuration table."""
    table = Table(title="Active Configuration", show_header=True, expand=True)
    table.add_column("Key", style="bold", width=22)
    table.add_column("Value", style="green")
    table.add_row("API_BASE_URL", API_BASE_URL)
    table.add_row("Streaming Mode", "Enabled" if streaming_mode else "Disabled")
    table.add_row("History File", HISTORY_FILE)
    console.print()
    console.print(table)
    console.print()

