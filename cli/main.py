"""Main CLI REPL loop and command dispatcher."""

import os
import sys
import time

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.history import FileHistory

from cli.config import HISTORY_FILE, console, pt_style
from cli.core.client import APIClient
from cli.core.completer import SlashCommandCompleter
from cli.core.stats import stats
from cli.handlers.chat import export_history, send_message_stream, send_message_sync
from cli.handlers.conversations import handle_conversations, handle_load
from cli.handlers.models import handle_models
from cli.handlers.usage import handle_account, handle_switch_account, handle_usage
from cli.ui.banners import print_banner
from cli.ui.panels import render_exit_panel

from cli.ui.tables import (
    render_config_table,
    render_help_table,
    render_history_table,
    render_status_table,
)


def main(clear_screen: bool = True, show_banner: bool = True) -> None:
    """Main CLI application loop."""
    if clear_screen:
        os.system("cls" if os.name == "nt" else "clear")
    if show_banner:
        print_banner()

    completer = SlashCommandCompleter()
    session: PromptSession = PromptSession(
        history=FileHistory(HISTORY_FILE),
        auto_suggest=AutoSuggestFromHistory(),
        completer=completer,
        style=pt_style,
    )

    streaming_mode = True
    next_is_new_chat = False

    while True:
        try:
            prompt_tag = "New Session" if next_is_new_chat else "Question"
            prompt_msg = [
                ("class:prompt_bracket", "╭─[ "),
                ("class:prompt_tag", prompt_tag),
                ("class:prompt_bracket", " ]\n╰─"),
                ("class:prompt_arrow", " > "),
            ]
            user_input = session.prompt(prompt_msg).strip()

            if not user_input:
                continue

            cmd_lower = user_input.lower()

            if cmd_lower in ("/exit", "/quit"):
                render_exit_panel(stats)
                break

            if cmd_lower == "/help":
                render_help_table()
                continue

            if cmd_lower == "/clear":
                os.system("cls" if os.name == "nt" else "clear")
                print_banner()
                continue

            if cmd_lower == "/status":
                try:
                    status_data = APIClient.get_status()
                    render_status_table(status_data)
                except Exception as exc:
                    console.print(f"[red]Error fetching status:[/red] {exc}\n")
                continue

            if cmd_lower == "/stats":
                stats.print_summary()
                continue

            if cmd_lower.startswith("/model"):
                parts = user_input.split(maxsplit=1)
                target = parts[1].strip() if len(parts) > 1 else None
                handle_models(target_model=target)
                continue

            if cmd_lower in ("/account", "/whoami", "/user", "/email"):
                handle_account()
                continue

            if cmd_lower in ("/switch-account", "/switch", "/logout", "/login"):
                handle_switch_account()
                continue

            if cmd_lower in ("/usage", "/quota", "/limit", "/limits"):
                handle_usage()
                continue

            if cmd_lower in ("/convs", "/chats", "/conversations"):
                handle_conversations()
                continue

            if cmd_lower.startswith("/load") or cmd_lower.startswith("/resume"):
                parts = user_input.split(maxsplit=1)
                target = parts[1].strip() if len(parts) > 1 else None
                handle_load(target)
                continue

            if cmd_lower == "/stream":
                streaming_mode = not streaming_mode
                status_str = "[green]ENABLED[/green]" if streaming_mode else "[yellow]DISABLED[/yellow]"
                console.print(f"[cyan]Streaming mode:[/cyan] {status_str}\n")
                continue

            if cmd_lower.startswith("/new"):
                parts = user_input.split(maxsplit=1)
                if len(parts) == 1:
                    console.print("\n[dim]Resetting Gemini session...[/dim]")
                    if APIClient.reset_chat():
                        console.print("[bold green]New conversation initialized successfully on Gemini.[/bold green]\n")
                    else:
                        next_is_new_chat = True
                        console.print("[yellow]The next message will be sent in a new session.[/yellow]\n")
                    continue
                else:
                    prompt_text = parts[1].strip()
                    if streaming_mode:
                        send_message_stream(prompt_text, new_chat=True)
                    else:
                        send_message_sync(prompt_text, new_chat=True)
                    continue

            if cmd_lower.startswith("/save"):
                parts = user_input.split(maxsplit=1)
                target_file = parts[1].strip() if len(parts) > 1 else None
                export_history(target_file)
                continue

            if cmd_lower == "/history":
                render_history_table(stats.history_entries)
                continue

            if cmd_lower == "/config":
                render_config_table(streaming_mode)
                continue

            # Send prompt
            is_new = next_is_new_chat
            next_is_new_chat = False

            if streaming_mode:
                send_message_stream(user_input, new_chat=is_new)
            else:
                send_message_sync(user_input, new_chat=is_new)

        except (KeyboardInterrupt, EOFError):
            render_exit_panel(stats)
            break
        except Exception as exc:
            console.print(f"\n[bold red]Unexpected error:[/bold red] {exc}\n")


if __name__ == "__main__":
    main()
