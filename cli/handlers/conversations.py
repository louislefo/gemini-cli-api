"""Conversation history listing and resumption handlers."""

from rich.panel import Panel
from rich.table import Table
from rich import box
from cli.config import console
from cli.core.client import APIClient
from cli.ui.menus import select_conversation_interactive

cached_conversations: list[dict] = []


def handle_conversations() -> list[dict]:
    """Fetches and displays saved conversations in a formatted responsive table."""
    global cached_conversations
    console.print("\n[dim]Fetching conversation history from Gemini...[/dim]")
    try:
        convs = APIClient.fetch_conversations()
        cached_conversations = convs

        if not convs:
            console.print("[yellow]No conversation history found on Gemini.[/yellow]\n")
            return []

        from cli.ui.banners import get_terminal_width
        term_width = get_terminal_width()
        max_title_len = max(20, term_width - 32)

        table = Table(show_header=True, header_style="bold green", box=box.ROUNDED, expand=True)
        table.add_column("#", style="dim", width=4)
        table.add_column("Title", style="bold white")
        table.add_column("ID", style="cyan", width=18)

        for idx, c in enumerate(convs[:20], 1):
            raw_title = c.get("title", "Untitled")
            title = raw_title[:max_title_len] + ("..." if len(raw_title) > max_title_len else "")
            table.add_row(str(idx), title, c.get("id", ""))

        panel = Panel(
            table,
            title=f"[bold green]Gemini Conversation History ({len(convs)} chats)[/bold green]",
            subtitle="[dim]Use /load [number|id] to resume a discussion[/dim]",
            border_style="green",
            box=box.ROUNDED,
            padding=(1, 2),
            expand=True,
        )
        console.print()
        console.print(panel)
        console.print()
        return convs

    except Exception as exc:
        console.print(f"[red]Error fetching conversations:[/red] {exc}\n")
        return []



def handle_load(target: str | None = None) -> None:
    """Resumes a past conversation by index or ID, or opens interactive selector."""
    global cached_conversations
    try:
        if not target:
            if not cached_conversations:
                console.print("\n[dim]Loading conversations list...[/dim]")
                cached_conversations = APIClient.fetch_conversations()

            if not cached_conversations:
                console.print("[yellow]No conversation history found to load.[/yellow]\n")
                return

            selected = select_conversation_interactive(cached_conversations)
            if selected:
                target_id = selected.get("id")
            else:
                console.print("[dim]Load cancelled.[/dim]\n")
                return
        else:
            target_id = target
            if target.isdigit() and cached_conversations:
                idx = int(target) - 1
                if 0 <= idx < len(cached_conversations):
                    target_id = cached_conversations[idx]["id"]

        console.print(f"\n[dim]Loading conversation {target_id}...[/dim]")
        res = APIClient.load_conversation(target_id)
        title = res.get("title", target_id)
        console.print(f"[bold green]Conversation resumed successfully:[/bold green] [bold cyan]{title}[/bold cyan]\n")

    except Exception as exc:
        console.print(f"[red]Error resuming conversation:[/red] {exc}\n")
