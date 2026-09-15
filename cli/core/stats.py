"""Session statistics tracking for the CLI."""

import datetime
import time
from rich.panel import Panel
from rich.table import Table
from rich import box
from cli.config import console


class SessionStats:
    """Tracks interactive session statistics and latency metrics."""

    def __init__(self) -> None:
        self.start_time = time.time()
        self.total_prompts = 0
        self.total_generation_time = 0.0
        self.total_chars_received = 0
        self.history_entries: list[dict] = []

    def record_interaction(self, prompt: str, response: str, duration: float) -> None:
        """Records a single prompt/response interaction."""
        self.total_prompts += 1
        self.total_generation_time += duration
        self.total_chars_received += len(response)
        self.history_entries.append({
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "prompt": prompt,
            "response": response,
            "duration": round(duration, 2),
        })

    def print_summary(self) -> None:
        """Renders session metrics summary table."""
        table = Table(show_header=True, header_style="bold magenta", box=box.SIMPLE_HEAD)
        table.add_column("Metric", style="cyan", width=28)
        table.add_column("Value", style="bold green")

        elapsed = round(time.time() - self.start_time, 1)
        avg_time = (
            round(self.total_generation_time / self.total_prompts, 2)
            if self.total_prompts > 0
            else 0.0
        )

        table.add_row("Session Duration", f"{elapsed}s")
        table.add_row("Requests Sent", str(self.total_prompts))
        table.add_row("Total Generation Time", f"{round(self.total_generation_time, 2)}s")
        table.add_row("Average Response Time", f"{avg_time}s")
        table.add_row("Total Characters Received", f"{self.total_chars_received:,}")

        panel = Panel(
            table,
            title="[bold magenta]Session Statistics[/bold magenta]",
            border_style="magenta",
            box=box.ROUNDED,
            padding=(1, 2),
        )
        console.print()
        console.print(panel)
        console.print()


stats = SessionStats()
