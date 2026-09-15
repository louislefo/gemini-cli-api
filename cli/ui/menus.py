"""Interactive arrow-key navigable selection menus for models and conversations."""

import os
import sys
from typing import Optional
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich import box
from cli.ui.banners import get_terminal_width


def _read_key() -> str:
    """Reads a single keypress or arrow key cross-platform."""
    if os.name == "nt":
        import msvcrt
        ch = msvcrt.getch()
        if ch in (b"\x00", b"\xe0"):
            ch2 = msvcrt.getch()
            if ch2 == b"H":
                return "UP"
            elif ch2 == b"P":
                return "DOWN"
        elif ch in (b"\r", b"\n"):
            return "ENTER"
        elif ch == b"\x1b":
            return "ESC"
        elif ch == b"\x03":
            raise KeyboardInterrupt()
        else:
            try:
                return ch.decode("utf-8")
            except Exception:
                return ""
    else:
        import termios
        import tty
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                ch2 = sys.stdin.read(1)
                if ch2 == "[":
                    ch3 = sys.stdin.read(1)
                    if ch3 == "A":
                        return "UP"
                    elif ch3 == "B":
                        return "DOWN"
                return "ESC"
            elif ch in ("\r", "\n"):
                return "ENTER"
            elif ch == "\x03":
                raise KeyboardInterrupt()
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
    return ""


def select_model_interactive(models_list: list[dict], current_model: str) -> Optional[dict]:
    """Displays an interactive menu to choose a model using Up/Down arrows and Enter."""
    if not models_list:
        return None

    selected_idx = 0
    for idx, m in enumerate(models_list):
        if m.get("is_active") or (m.get("id") in current_model.lower()):
            selected_idx = idx
            break

    def render_table(cur_idx: int) -> Panel:
        tbl = Table(show_header=True, header_style="bold cyan", box=box.SIMPLE, expand=True)
        tbl.add_column(" ", width=2)
        tbl.add_column("#", width=3, style="dim")
        tbl.add_column("Model ID", style="bold yellow", width=14)
        tbl.add_column("Display Name", style="white")
        tbl.add_column("State", width=10)

        for i, m in enumerate(models_list):
            is_cursor = (i == cur_idx)
            cursor_str = "[bold cyan]>[/bold cyan]" if is_cursor else " "
            row_num = f"{i + 1}"
            mod_id = m.get("id", "")
            name = m.get("name", "")
            active_badge = "[bold green]ACTIVE[/bold green]" if m.get("is_active") else "[dim]Available[/dim]"

            if is_cursor:
                tbl.add_row(
                    cursor_str,
                    f"[bold cyan]{row_num}[/bold cyan]",
                    f"[bold cyan]{mod_id}[/bold cyan]",
                    f"[bold white]{name}[/bold white]",
                    active_badge,
                    style="on grey23",
                )
            else:
                tbl.add_row(cursor_str, row_num, mod_id, name, active_badge)

        return Panel(
            tbl,
            title="[bold cyan]Select Gemini Model (Up/Down arrows, Enter, Esc)[/bold cyan]",
            border_style="cyan",
            box=box.ROUNDED,
            padding=(1, 2),
            expand=True,
        )

    try:
        with Live(render_table(selected_idx), refresh_per_second=20, transient=True) as live:
            while True:
                key = _read_key()
                if key == "UP":
                    selected_idx = (selected_idx - 1) % len(models_list)
                    live.update(render_table(selected_idx))
                elif key == "DOWN":
                    selected_idx = (selected_idx + 1) % len(models_list)
                    live.update(render_table(selected_idx))
                elif key == "ENTER":
                    return models_list[selected_idx]
                elif key == "ESC":
                    return None
                elif key in ("1", "2", "3", "4", "5", "6", "7", "8", "9"):
                    digit_idx = int(key) - 1
                    if 0 <= digit_idx < len(models_list):
                        return models_list[digit_idx]
    except (KeyboardInterrupt, Exception):
        return None


def select_conversation_interactive(convs_list: list[dict]) -> Optional[dict]:
    """Displays an interactive menu to choose a conversation using Up/Down arrows and Enter."""
    if not convs_list:
        return None

    selected_idx = 0
    max_display = min(len(convs_list), 15)

    def render_table(cur_idx: int) -> Panel:
        term_width = get_terminal_width()
        max_title_len = max(20, term_width - 36)

        tbl = Table(show_header=True, header_style="bold green", box=box.SIMPLE, expand=True)
        tbl.add_column(" ", width=2)
        tbl.add_column("#", width=3, style="dim")
        tbl.add_column("Title", style="bold white")
        tbl.add_column("ID", style="dim cyan", width=18)

        for i in range(max_display):
            c = convs_list[i]
            is_cursor = (i == cur_idx)
            cursor_str = "[bold green]>[/bold green]" if is_cursor else " "
            row_num = f"{i + 1}"
            raw_title = c.get("title", "Untitled")
            title = raw_title[:max_title_len] + ("..." if len(raw_title) > max_title_len else "")
            cid = c.get("id", "")

            if is_cursor:
                tbl.add_row(
                    cursor_str,
                    f"[bold green]{row_num}[/bold green]",
                    f"[bold white]{title}[/bold white]",
                    f"[bold cyan]{cid}[/bold cyan]",
                    style="on grey23",
                )
            else:
                tbl.add_row(cursor_str, row_num, title, cid)

        return Panel(
            tbl,
            title=f"[bold green]Select Conversation ({len(convs_list)} found)[/bold green]",
            subtitle="[dim]Use Up/Down arrows, Enter to validate, Esc to cancel[/dim]",
            border_style="green",
            box=box.ROUNDED,
            padding=(1, 2),
            expand=True,
        )

    try:
        with Live(render_table(selected_idx), refresh_per_second=20, transient=True) as live:
            while True:
                key = _read_key()
                if key == "UP":
                    selected_idx = (selected_idx - 1) % max_display
                    live.update(render_table(selected_idx))
                elif key == "DOWN":
                    selected_idx = (selected_idx + 1) % max_display
                    live.update(render_table(selected_idx))
                elif key == "ENTER":
                    return convs_list[selected_idx]
                elif key == "ESC":
                    return None
                elif key.isdigit() and int(key) > 0:
                    digit_idx = int(key) - 1
                    if 0 <= digit_idx < max_display:
                        return convs_list[digit_idx]
    except (KeyboardInterrupt, Exception):
        return None

