import os
import sys

# Auto-switch to project .venv interpreter if invoked with system Python
_repo_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_venv_python = (
    os.path.join(_repo_dir, ".venv", "Scripts", "python.exe")
    if sys.platform == "win32"
    else os.path.join(_repo_dir, ".venv", "bin", "python")
)
if os.path.isfile(_venv_python) and os.path.abspath(sys.executable).lower() != os.path.abspath(_venv_python).lower():
    import subprocess
    try:
        sys.exit(subprocess.call([_venv_python] + sys.argv))
    except KeyboardInterrupt:
        sys.exit(0)

# Ensure project root is at the head of sys.path
if _repo_dir not in sys.path:
    sys.path.insert(0, _repo_dir)

import time
import unittest

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def run_all_tests() -> bool:
    """Discovers and runs all unit tests in the tests directory."""
    start_time = time.time()

    loader = unittest.TestLoader()
    suite = loader.discover(
        start_dir=os.path.dirname(os.path.abspath(__file__)),
        pattern="test_*.py",
    )

    console.print(Panel(
        "[bold cyan]Running GEMINI-CLI-API Test Suite[/bold cyan]\n"
        "[dim]Discovering and executing tests for API, Schemas, Auth/CDP, CLI Core, and UI...[/dim]",
        border_style="cyan",
        box=box.ROUNDED,
    ))

    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    duration = round(time.time() - start_time, 2)
    success = result.wasSuccessful()

    table = Table(title="Test Execution Summary", box=box.ROUNDED, expand=True)
    table.add_column("Category", style="bold white", width=25)
    table.add_column("Count", style="bold cyan", width=12)
    table.add_column("Status", style="bold")

    table.add_row("Total Tests Run", str(result.testsRun), "[bold green]PASS[/bold green]" if success else "[bold red]FAIL[/bold red]")
    table.add_row("Failures", str(len(result.failures)), "[bold red]FAIL[/bold red]" if result.failures else "[green]0[/green]")
    table.add_row("Errors", str(len(result.errors)), "[bold red]ERROR[/bold red]" if result.errors else "[green]0[/green]")
    table.add_row("Skipped", str(len(result.skipped)), "[yellow]0[/yellow]" if not result.skipped else str(len(result.skipped)))
    table.add_row("Total Duration", f"{duration}s", "[dim]Completed[/dim]")

    console.print()
    console.print(table)
    console.print()

    if success:
        console.print(f"[bold green]All {result.testsRun} tests passed successfully in {duration}s![/bold green]\n")
    else:
        console.print(f"[bold red]Tests completed with failures or errors ({len(result.failures)} failures, {len(result.errors)} errors).[/bold red]\n")

    return success


if __name__ == "__main__":
    ok = run_all_tests()
    sys.exit(0 if ok else 1)
