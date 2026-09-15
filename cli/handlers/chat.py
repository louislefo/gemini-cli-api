"""Chat execution handlers (streaming, sync, export)."""

import datetime
import json
import time
import urllib.error
import urllib.request
from rich.live import Live
from rich.panel import Panel
from rich.text import Text
from rich import box
from cli.config import API_BASE_URL, console
from cli.core.stats import stats
from cli.ui.panels import render_error_panel, render_response_panel


def send_message_stream(prompt: str, new_chat: bool = False, model: str | None = None) -> None:
    """Sends a message to Gemini with a transient live preview and a clean structured final markdown panel."""
    url = f"{API_BASE_URL}/chat/stream"
    payload = {"prompt": prompt, "new_chat": new_chat, "model": model}
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    start_time = time.time()
    accumulated_text = ""
    full_text_result = ""

    console.print()
    try:
        with Live(
            Panel(Text("Waiting for Gemini response...", style="dim"), title="[cyan]Generating[/cyan]", border_style="cyan", box=box.SIMPLE),
            refresh_per_second=12,
            transient=True,
        ) as live:
            with urllib.request.urlopen(req, timeout=180) as response:
                for raw_line in response:
                    line = raw_line.decode("utf-8").strip()
                    if line.startswith("data:"):
                        raw_data = line[5:].strip()
                        if raw_data == "[DONE]":
                            break
                        try:
                            data = json.loads(raw_data)
                            if "status" in data and data["status"] == "done" and "full_text" in data:
                                full_text_result = data["full_text"]
                            elif "chunk" in data:
                                chunk = data["chunk"]
                                accumulated_text += chunk
                                if "full_text" in data and data["full_text"]:
                                    full_text_result = data["full_text"]

                                preview = accumulated_text[-1000:] if len(accumulated_text) > 1000 else accumulated_text
                                live.update(
                                    Panel(
                                        Text(preview, style="white"),
                                        title=f"[cyan]Generating ({len(accumulated_text)} chars)...[/cyan]",
                                        border_style="cyan",
                                        box=box.SIMPLE,
                                    )
                                )
                            elif "error" in data:
                                console.print(f"\n[bold red]Error: {data['error']}[/bold red]")
                        except Exception:
                            pass

        final_response = full_text_result if full_text_result else accumulated_text
        duration = time.time() - start_time
        stats.record_interaction(prompt, final_response, duration)
        render_response_panel(final_response, duration)

    except urllib.error.HTTPError as err:
        try:
            err_data = json.loads(err.read().decode("utf-8"))
            render_error_panel(f"HTTP Error {err.code}: {err_data.get('detail')}")
        except Exception:
            render_error_panel(f"HTTP Error {err.code}: {err.reason}")
    except Exception as exc:
        render_error_panel(f"Communication Error: {exc}")


def send_message_sync(prompt: str, new_chat: bool = False, model: str | None = None) -> None:
    """Sends a message in synchronous mode and displays the response in a structured panel."""
    url = f"{API_BASE_URL}/chat"
    payload = {"prompt": prompt, "new_chat": new_chat, "model": model}
    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    console.print("\n[dim]Waiting for response...[/dim]")
    start_time = time.time()

    try:
        with urllib.request.urlopen(req, timeout=180) as response:
            result = json.loads(response.read().decode("utf-8"))
            duration = time.time() - start_time
            response_text = result.get("response", "")

            stats.record_interaction(prompt, response_text, duration)
            render_response_panel(response_text, duration)
    except Exception as exc:
        render_error_panel(f"Error: {exc}")


def export_history(filename: str | None = None) -> None:
    """Exports active conversation session to a Markdown file."""
    if not stats.history_entries:
        console.print("[yellow]No conversation history to export.[/yellow]\n")
        return

    if not filename:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"gemini_chat_{timestamp}.md"

    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(f"# Gemini Conversation Export - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            for idx, item in enumerate(stats.history_entries, 1):
                f.write(f"## Message {idx} ({item['timestamp']} - {item['duration']}s)\n\n")
                f.write(f"**User:**\n\n{item['prompt']}\n\n")
                f.write(f"**Gemini:**\n\n{item['response']}\n\n")
                f.write("---\n\n")

        console.print(f"[green]History exported successfully to:[/green] [bold]{filename}[/bold]\n")
    except Exception as exc:
        console.print(f"[red]Error exporting history:[/red] {exc}\n")
