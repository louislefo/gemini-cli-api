import os
import sys

# Auto-switch to project .venv interpreter if invoked with system Python
_repo_dir = os.path.dirname(os.path.abspath(__file__))
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

import argparse
import asyncio
import os
import shutil
import sys
import threading
import time
import urllib.request
from typing import Optional

from rich.console import Console
from rich.panel import Panel

from auth import (
    DEFAULT_CDP_PORT,
    DEFAULT_PROFILE_DIR,
    check_auth_fast,
    check_authentication_status,
    find_chrome_executable,
    get_account_info_fast,
    is_cdp_ready,
    launch_chrome_process,
    run_login_flow,
    stop_chrome,
)
from cli.ui.banners import print_banner
from cli.ui.menus import select_mode_interactive

console = Console()

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


def _start_background_uvicorn(host: str, port: int) -> None:
    """Runs Uvicorn in a background daemon thread."""
    import uvicorn
    from app.main import app

    config = uvicorn.Config(
        app,
        host=host,
        port=port,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)
    server.run()


def wait_for_api_ready(base_url: str, timeout_sec: int = 15) -> bool:
    """Waits until the FastAPI backend responds to /health requests."""
    start = time.time()
    while time.time() - start < timeout_sec:
        try:
            req = urllib.request.Request(f"{base_url}/health")
            with urllib.request.urlopen(req, timeout=1.0) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(0.3)
    return False


def ensure_authenticated_and_headless(chrome_path: str, cdp_port: int, profile_dir: str) -> tuple[Optional[object], dict]:
    """Checks authentication status, runs interactive login if needed, and launches headless Chrome."""
    chrome_proc = None
    account_info = {"email": "Unknown", "name": "Unknown", "tier": "Free (Standard)"}

    # 1. If CDP is not already running, launch headless Chrome pointing to Gemini
    if not is_cdp_ready(cdp_port):
        console.print("[dim]Connecting to background Gemini session...[/dim]")
        chrome_proc = launch_chrome_process(
            chrome_path=chrome_path,
            profile_dir=profile_dir,
            port=cdp_port,
            headless=True,
            url="https://gemini.google.com/app",
        )
        for _ in range(15):
            if is_cdp_ready(cdp_port):
                break
            time.sleep(0.4)

    # 2. Check authentication status and retrieve account info
    time.sleep(1.2)
    try:
        auth_data = asyncio.run(check_authentication_status(cdp_port))
    except Exception:
        auth_data = {"authenticated": False}

    # 3. If authentication is missing, trigger interactive login
    if not auth_data.get("authenticated", False):
        if chrome_proc:
            try:
                chrome_proc.terminate()
            except Exception:
                pass
            chrome_proc = None
        stop_chrome(cdp_port)

        console.print(Panel.fit(
            "[bold yellow]Google Authentication Required[/bold yellow]\n\n"
            "Opening a visible Google Chrome window.\n"
            "Please sign in with your Google account at:\n"
            "[bold cyan]https://gemini.google.com/app[/bold cyan]\n\n"
            "Once authenticated, the window will automatically close and return here.",
            border_style="yellow",
        ))

        login_ok = asyncio.run(run_login_flow(chrome_path, profile_dir, cdp_port))
        if not login_ok:
            console.print("[bold red]Authentication failed or cancelled. Exiting.[/bold red]")
            sys.exit(1)

        # Relaunch headless Chrome with the persistent profile
        console.print("[bold cyan]Launching headless Chrome engine...[/bold cyan]")
        chrome_proc = launch_chrome_process(
            chrome_path=chrome_path,
            profile_dir=profile_dir,
            port=cdp_port,
            headless=True,
            url="https://gemini.google.com/app",
        )
        for _ in range(15):
            if is_cdp_ready(cdp_port):
                break
            time.sleep(0.4)

        try:
            account_info = asyncio.run(get_account_info_fast(cdp_port))
        except Exception:
            pass
    else:
        account_info = auth_data.get("account", account_info)
        console.print("[bold green]Authenticated Gemini session confirmed.[/bold green]")

    return chrome_proc, account_info


def main():
    """Main application orchestrator."""
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    parser = argparse.ArgumentParser(description="GEMINI-CLI-API: High-performance Gemini Chrome CDP Bridge & CLI")
    parser.add_argument("--api", action="store_true", help="Start FastAPI API server in foreground")
    parser.add_argument("--cli", action="store_true", help="Start interactive terminal CLI directly")
    parser.add_argument("--both", action="store_true", help="Start FastAPI API in background and launch terminal CLI")
    parser.add_argument("--logout", action="store_true", help="Log out, terminate background Chrome, and reset local profile")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="API server host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="API server port (default: 8000)")
    parser.add_argument("--cdp-port", type=int, default=DEFAULT_CDP_PORT, help="Chrome CDP port (default: 9222)")
    parser.add_argument("--profile", type=str, default=DEFAULT_PROFILE_DIR, help="Chrome user profile directory")

    args = parser.parse_args()

    if args.logout:
        stop_chrome(args.cdp_port)
        time.sleep(0.8)
        if os.path.exists(args.profile):
            try:
                shutil.rmtree(args.profile)
                console.print(f"\n[bold green]Successfully logged out and removed profile directory:[/bold green] {args.profile}")
            except Exception:
                shutil.rmtree(args.profile, ignore_errors=True)
                console.print(f"\n[bold green]Successfully logged out and cleared profile files in:[/bold green] {args.profile}")
        else:
            console.print("\n[bold green]No active profile directory found.[/bold green]")
        console.print("[dim]Run [bold white]gemini-cli-api[/bold white] or [bold white]python run.py[/bold white] to start the interactive authentication flow.[/dim]\n")
        return

    chrome_path = find_chrome_executable()
    if not chrome_path:
        console.print("[bold red]Error: Google Chrome executable could not be found on this system.[/bold red]")
        sys.exit(1)

    # 1. Welcome Banner (initially Disconnected)
    print_banner(connected=False)

    # 2. Authenticate & launch background headless Chrome
    chrome_proc, account_info = ensure_authenticated_and_headless(chrome_path, args.cdp_port, args.profile)

    # Clear screen and display active Connected banner with account info
    os.system("cls" if os.name == "nt" else "clear")
    print_banner(connected=True, account_info=account_info)

    # 3. Determine execution mode
    mode = None
    if args.api:
        mode = "api"
    elif args.cli:
        mode = "cli"
    elif args.both:
        mode = "both"
    else:
        mode = select_mode_interactive()

    # Handle interactive account switching if requested before starting
    while mode == "switch_account":
        if chrome_proc:
            try:
                chrome_proc.terminate()
            except Exception:
                pass
            chrome_proc = None
        stop_chrome(args.cdp_port)
        time.sleep(0.8)

        console.print(Panel.fit(
            "[bold cyan]Switching Google Account[/bold cyan]\n\n"
            "Opening a visible Google Chrome window.\n"
            "Please sign in or switch to your desired Google account at:\n"
            "[bold cyan]https://gemini.google.com/app[/bold cyan]\n\n"
            "Once authenticated, the window will automatically close and return here.",
            border_style="cyan",
        ))

        login_ok = asyncio.run(run_login_flow(chrome_path, args.profile, args.cdp_port))
        if not login_ok:
            console.print("[bold red]Account switch cancelled or failed.[/bold red]")

        # Relaunch headless Chrome
        chrome_proc = launch_chrome_process(
            chrome_path=chrome_path,
            profile_dir=args.profile,
            port=args.cdp_port,
            headless=True,
            url="https://gemini.google.com/app",
        )
        for _ in range(15):
            if is_cdp_ready(args.cdp_port):
                break
            time.sleep(0.4)

        try:
            account_info = asyncio.run(get_account_info_fast(args.cdp_port))
        except Exception:
            pass

        os.system("cls" if os.name == "nt" else "clear")
        print_banner(connected=True, account_info=account_info)
        mode = select_mode_interactive()

    base_url = f"http://{args.host}:{args.port}"

    try:
        if mode == "api":
            os.system("cls" if os.name == "nt" else "clear")
            print_banner(connected=True, account_info=account_info)
            console.print(Panel(
                f"[bold green]GEMINI-CLI-API Server Running[/bold green]\n\n"
                f"[white]API Endpoint    :[/white] [bold cyan]{base_url}[/bold cyan]\n"
                f"[white]Swagger Docs    :[/white] [bold cyan]{base_url}/docs[/bold cyan]\n"
                f"[white]ReDoc Docs      :[/white] [bold cyan]{base_url}/redoc[/bold cyan]\n"
                f"[white]Chrome CDP Port :[/white] [bold yellow]{args.cdp_port}[/bold yellow] [dim](Headless Engine)[/dim]",
                title="[bold cyan]API Server Mode[/bold cyan]",
                border_style="cyan",
                expand=True,
            ))
            import uvicorn
            uvicorn.run(
                "app.main:app",
                host=args.host,
                port=args.port,
                reload=False,
            )

        elif mode == "cli":
            console.print("[dim]Starting background API server...[/dim]")
            t = threading.Thread(target=_start_background_uvicorn, args=(args.host, args.port), daemon=True)
            t.start()

            if not wait_for_api_ready(base_url):
                console.print("[bold red]Failed to start background API server.[/bold red]")
                sys.exit(1)

            os.system("cls" if os.name == "nt" else "clear")
            print_banner(connected=True, account_info=account_info)
            from cli.main import main as cli_main
            cli_main(clear_screen=False, show_banner=False)

        elif mode == "both":
            console.print("[dim]Starting background API server...[/dim]")
            t = threading.Thread(target=_start_background_uvicorn, args=(args.host, args.port), daemon=True)
            t.start()

            if not wait_for_api_ready(base_url):
                console.print("[bold red]Failed to start background API server.[/bold red]")
                sys.exit(1)

            os.system("cls" if os.name == "nt" else "clear")
            print_banner(connected=True, account_info=account_info)
            console.print(Panel(
                f"[bold green]GEMINI-CLI-API Server Active in Background[/bold green]\n\n"
                f"[white]API Endpoint :[/white] [bold cyan]{base_url}[/bold cyan]\n"
                f"[white]Swagger Docs :[/white] [bold cyan]{base_url}/docs[/bold cyan]\n"
                f"[white]Chrome CDP   :[/white] [bold yellow]{args.cdp_port}[/bold yellow] [dim](Headless Engine)[/dim]",
                title="[bold cyan]Background API Server Info[/bold cyan]",
                border_style="cyan",
                expand=True,
            ))

            from cli.main import main as cli_main
            cli_main(clear_screen=False, show_banner=False)

    except KeyboardInterrupt:
        from cli.ui.panels import render_exit_panel
        render_exit_panel()
    finally:
        if chrome_proc:
            try:
                chrome_proc.terminate()
            except Exception:
                pass


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass

