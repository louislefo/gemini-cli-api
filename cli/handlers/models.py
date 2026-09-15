"""Model selection and switching slash command handler."""

from cli.config import console
from cli.core.client import APIClient
from cli.ui.menus import select_model_interactive


def handle_models(target_model: str | None = None) -> None:
    """Handles /model command: switches model directly or opens interactive menu."""
    try:
        data = APIClient.fetch_models()
        current = data.get("current_model", "Flash")
        models_list = data.get("models", [])

        if not target_model:
            selected = select_model_interactive(models_list, current)
            if selected:
                target_model = selected.get("id") or selected.get("name")
            else:
                console.print("[dim]Selection cancelled.[/dim]\n")
                return

        console.print(f"\n[dim]Switching model to: {target_model}...[/dim]")
        res = APIClient.switch_model(target_model)
        new_model = res.get("current_model", target_model)
        console.print(f"[bold green]Active model updated to:[/bold green] [bold cyan]{new_model}[/bold cyan]\n")

    except Exception as exc:
        console.print(f"[red]Error managing models:[/red] {exc}\n")
