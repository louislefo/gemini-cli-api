"""Banner, ASCII header, and input box border components."""

import shutil
from rich.panel import Panel
from rich.text import Text
from rich import box
from cli.config import VERSION, console
from cli.core.client import APIClient


def get_terminal_width() -> int:
    """Returns the current terminal width dynamically."""
    try:
        cols = shutil.get_terminal_size((80, 24)).columns
        return cols if cols > 10 else 80
    except Exception:
        return getattr(console, "width", 80) or 80


def print_prompt_box_top(tag: str = "Question") -> None:
    """Prints the top border of the input box matching dynamic terminal width."""
    width = max(30, get_terminal_width() - 2)
    prefix = f"╭── {tag} "
    remaining = max(0, width - len(prefix) - 1)
    console.print(f"[bright_black]{prefix}{'─' * remaining}╮[/bright_black]")


def print_prompt_box_bottom() -> None:
    """Prints the bottom border of the input box matching dynamic terminal width."""
    width = max(30, get_terminal_width() - 2)
    console.print(f"[bright_black]╰{'─' * (width - 1)}╯[/bright_black]")


def print_banner(connected: bool | None = None, account_info: dict | None = None) -> None:
    """Displays the welcome banner with responsive layout based on terminal size."""
    term_width = get_terminal_width()

    logo_art = """
   ____ _____ __  __ ___ _   _ ___        ____ _     ___         _    ____ ___ 
  / ___| ____|  \/  |_ _| \ | |_ _|      / ___| |   |_ _|       / \  |  _ \_ _|
 | |  _|  _| | |\/| || ||  \| || | _____| |   | |    | | _____ / _ \ | |_) | | 
 | |_| | |___| |  | || || |\  || ||_____| |___| |___ | ||_____/ ___ \|  __/| | 
  \____|_____|_|  |_|___|_| \_|___|      \____|_____|___|    /_/   \_\_|  |___|
"""

    logo_medium = """
   ____ _____ __  __ ___ _   _ ___       ____ _     ___ 
  / ___| ____|  \/  |_ _| \ | |_ _|     / ___| |   |_ _|
 | |  _|  _| | |\/| || ||  \| || | ___ | |   | |    | | 
 | |_| | |___| |  | || || |\  || ||___|| |___| |___ | | 
  \____|_____|_|  |_|___|_| \_|___|     \____|_____|___|
"""

    if connected is None:
        is_ok, _ = APIClient.get_quick_status()
    else:
        is_ok = connected

    status_str = "Connected (Port 9222)" if is_ok else "Disconnected"
    status_style = "bold green" if is_ok else "bold red"

    console.print()
    if term_width >= 82:
        console.print(Text(logo_art, style="bold cyan"))
    elif term_width >= 58:
        console.print(Text(logo_medium, style="bold cyan"))
    else:
        compact_title = Text()
        compact_title.append("=== ", style="bold cyan")
        compact_title.append("GEMINI-CLI-API", style="bold white")
        compact_title.append(" ===", style="bold cyan")
        console.print(compact_title)

    header_info = Text()
    header_info.append("  GEMINI-CLI-API ", style="bold white")
    header_info.append(f"v{VERSION}", style="dim white")
    header_info.append(" | Status: ", style="dim")
    header_info.append(f"[{status_str}]", style=status_style)
    header_info.append(" | Type ", style="dim")
    header_info.append("/help", style="bold yellow")
    header_info.append(" for commands", style="dim")

    acc = account_info
    if is_ok and acc is None:
        try:
            acc = APIClient.fetch_account()
        except Exception:
            acc = None

    if is_ok and acc:
        email = acc.get("email", "")
        tier = acc.get("tier", "Free (Standard)")
        if email and email != "Unknown":
            tier_color = "bold magenta" if ("pro" in tier.lower() or "advanced" in tier.lower()) else "bold green"
            header_info.append("\n  Account: ", style="dim")
            header_info.append(email, style="bold white")
            header_info.append(" | Plan: ", style="dim")
            header_info.append(f"[{tier}]", style=tier_color)

    header_info.append("\n")
    console.print(header_info)

    card_text = Text()
    card_text.append("  Quick commands: ", style="dim")
    card_text.append("/model", style="bold white")
    card_text.append(" (select model) | ", style="dim")
    card_text.append("/account", style="bold white")
    card_text.append(" (account info) | ", style="dim")
    card_text.append("/usage", style="bold white")
    card_text.append(" (Pro quotas) | ", style="dim")
    card_text.append("/help", style="bold white")
    card_text.append(" (full help)\n", style="dim")
    card_text.append("  Type your prompt directly in the box below to start chatting.", style="dim italic")

    panel = Panel(
        card_text,
        border_style="bright_black",
        box=box.ROUNDED,
        padding=(0, 2),
        expand=True,
    )
    console.print(panel)
    console.print()

