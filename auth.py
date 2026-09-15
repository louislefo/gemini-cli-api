"""Chrome Authentication and Headless Launcher Manager.

Provides automated workflows to authenticate Google Gemini in a visible Chrome window,
verify login status, and launch Chrome in headless mode for the FastAPI backend.
"""

import argparse
import asyncio
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import json
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

DEFAULT_CDP_PORT = 9222
DEFAULT_PROFILE_DIR = os.path.abspath(os.path.expanduser(os.path.join("~", ".chrome_gemini_profile")))
GEMINI_URL = "https://gemini.google.com/app"
GOOGLE_LOGIN_URL = "https://accounts.google.com/AccountChooser?continue=https%3A%2F%2Fgemini.google.com%2Fapp"


def find_chrome_executable() -> Optional[str]:
    """Auto-detects the Google Chrome or Chromium executable on Windows, macOS, and Linux."""
    if sys.platform == "win32":
        candidates = [
            os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "Google", "Chrome", "Application", "chrome.exe"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe"),
        ]
        for path in candidates:
            if os.path.isfile(path):
                return path
        which = shutil.which("chrome") or shutil.which("google-chrome")
        return which

    elif sys.platform == "darwin":
        candidates = [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            os.path.expanduser("~/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        ]
        for path in candidates:
            if os.path.isfile(path):
                return path
        return shutil.which("google-chrome")

    else:
        # Linux
        for name in ["google-chrome", "google-chrome-stable", "chromium", "chromium-browser"]:
            which = shutil.which(name)
            if which:
                return which
        for path in ["/usr/bin/google-chrome", "/usr/bin/google-chrome-stable", "/usr/bin/chromium", "/usr/bin/chromium-browser"]:
            if os.path.isfile(path):
                return path
    return None


def is_cdp_ready(port: int = DEFAULT_CDP_PORT) -> bool:
    """Checks if Chrome DevTools Protocol is responding on the specified port."""
    try:
        url = f"http://127.0.0.1:{port}/json/version"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return "webSocketDebuggerUrl" in data or "Browser" in data
    except Exception:
        return False


def launch_chrome_process(
    chrome_path: str,
    profile_dir: str,
    port: int = DEFAULT_CDP_PORT,
    headless: bool = False,
    url: Optional[str] = None,
) -> subprocess.Popen:
    """Launches Google Chrome with remote debugging and persistent user profile."""
    norm_profile = os.path.abspath(os.path.normpath(profile_dir))
    os.makedirs(norm_profile, exist_ok=True)

    target_url = url if url else ("about:blank" if headless else GEMINI_URL)

    args = [
        chrome_path,
        f"--remote-debugging-port={port}",
        "--remote-allow-origins=*",
        f"--user-data-dir={norm_profile}",
        "--profile-directory=Default",
        "--no-first-run",
        "--no-default-browser-check",
        "--window-size=1920,1080",
        "--disable-blink-features=AutomationControlled",
    ]

    if headless:
        args.extend([
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--mute-audio",
        ])

    args.append(target_url)

    creationflags = 0
    if sys.platform == "win32":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

    process = subprocess.Popen(
        args,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
        creationflags=creationflags,
        close_fds=True if sys.platform != "win32" else False,
    )
    return process


def stop_chrome(port: int = DEFAULT_CDP_PORT) -> bool:
    """Terminates Chrome processes using the debugging port or dedicated profile."""
    stopped = False
    if sys.platform == "win32":
        try:
            # 1. Kill any process listening on the port
            cmd = f'netstat -ano | findstr :{port}'
            output = subprocess.check_output(cmd, shell=True, text=True)
            pids = set()
            for line in output.strip().splitlines():
                parts = line.strip().split()
                if len(parts) >= 5 and "LISTENING" in parts:
                    pid = parts[-1]
                    if pid.isdigit() and pid != "0":
                        pids.add(int(pid))
            for pid in pids:
                try:
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)], capture_output=True)
                    stopped = True
                except Exception:
                    pass
        except Exception:
            pass

        try:
            # 2. Also kill any orphan Chrome processes using the remote port or profile
            ps_cmd = f"Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | Where-Object {{ $_.CommandLine -like '*remote-debugging-port={port}*' -or $_.CommandLine -like '*chrome_gemini_profile*' }} | ForEach-Object {{ Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }}"
            subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True)
            stopped = True
        except Exception:
            pass
    else:
        try:
            subprocess.run(["pkill", "-9", "-f", f"--remote-debugging-port={port}"], capture_output=True)
            subprocess.run(["pkill", "-9", "-f", "chrome_gemini_profile"], capture_output=True)
            stopped = True
        except Exception:
            pass
    return stopped


def get_cdp_tabs(port: int = DEFAULT_CDP_PORT) -> list[dict]:
    """Retrieves list of active tabs directly via Chrome DevTools HTTP JSON API."""
    try:
        url = f"http://127.0.0.1:{port}/json/list"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except Exception:
        return []


def check_auth_fast(port: int = DEFAULT_CDP_PORT) -> dict:
    """Fast, lightweight verification of authentication status."""
    if not is_cdp_ready(port):
        return {"connected": False, "authenticated": False, "details": "CDP port inactive."}

    tabs = get_cdp_tabs(port)
    for tab in tabs:
        url = tab.get("url", "")
        if "accounts.google.com" in url or "signin" in url.lower():
            return {"connected": True, "authenticated": False, "page_url": url, "details": "Google sign-in page detected."}

    # Inconclusive without DOM check
    return {"connected": True, "authenticated": None, "details": "CDP active. Needs DOM verification."}


async def check_authentication_status(port: int = DEFAULT_CDP_PORT) -> dict:
    """Verifies if Gemini is logged in by inspecting the active DOM for the chat prompt input."""
    if not is_cdp_ready(port):
        return {"connected": False, "authenticated": False, "details": "CDP port inactive."}

    tabs = get_cdp_tabs(port)
    for tab in tabs:
        url = tab.get("url", "")
        if "accounts.google.com" in url:
            return {"connected": True, "authenticated": False, "page_url": url, "details": "Google sign-in page detected."}

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        return {"connected": True, "authenticated": False, "details": "Playwright unavailable."}

    result = {
        "connected": True,
        "authenticated": False,
        "page_url": "",
        "page_title": "",
        "details": "Checking Gemini prompt element...",
    }

    try:
        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
            context = browser.contexts[0] if browser.contexts else None
            if not context:
                result["details"] = "No browser context found."
                return result

            gemini_page = None
            for page in context.pages:
                if "gemini.google.com" in page.url:
                    gemini_page = page
                    break

            if not gemini_page:
                gemini_page = await context.new_page()
                await gemini_page.goto(GEMINI_URL, wait_until="domcontentloaded", timeout=15000)

            result["page_url"] = gemini_page.url
            try:
                result["page_title"] = await gemini_page.title()
            except Exception:
                pass

            if "accounts.google.com" in gemini_page.url:
                result["authenticated"] = False
                result["details"] = "On Google sign-in page."
                return result

            try:
                acc_data = await gemini_page.evaluate("""() => {
                    let email = '';
                    let name = '';
                    let tier = 'Free (Standard)';

                    const accSelectors = [
                        "a[aria-label*='Compte Google']",
                        "a[aria-label*='Google Account']",
                        "button[aria-label*='Compte Google']",
                        "button[aria-label*='Google Account']",
                        "[aria-label*='@']",
                        "a[href*='SignOutOptions']",
                        "a[href*='accounts.google.com']",
                        "button[data-test-id='user-profile-button']",
                        ".gb_A",
                        ".gb_d",
                        ".gb_f",
                        "img[alt*='Photo de profil']",
                        "img[alt*='Profile photo']"
                    ];

                    for (const sel of accSelectors) {
                        const els = document.querySelectorAll(sel);
                        for (const el of els) {
                            const aria = el.getAttribute('aria-label') || el.getAttribute('title') || el.getAttribute('alt') || '';
                            const emailMatch = aria.match(/([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,})/);
                            if (emailMatch && !email) {
                                email = emailMatch[1];
                            }
                            const nameMatch = aria.match(/(?:Compte Google|Google Account)\\s*:\\s*([^(\\n]+)/i);
                            if (nameMatch && !name) {
                                name = nameMatch[1].trim();
                            }
                        }
                    }

                    if (!email) {
                        const allAria = Array.from(document.querySelectorAll('[aria-label]')).map(e => e.getAttribute('aria-label')).join(' ');
                        const m = allAria.match(/([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,})/);
                        if (m) email = m[1];
                    }

                    const signInBtn = document.querySelector("a[href*='accounts.google.com/ServiceLogin'], a[aria-label*='Se connecter'], a[aria-label*='Sign in'], button[aria-label*='Se connecter'], button[aria-label*='Sign in']");
                    const bodyText = (document.body ? document.body.innerText : '').slice(0, 3000);
                    const isGuest = !email || signInBtn !== null || /\\b(Se connecter|Sign in)\\b/i.test(bodyText);

                    const advBadge = document.querySelector("[aria-label*='Advanced'], [aria-label*='Pro'], .subscription-badge, .tier-pill, mat-chip, .sparkle-container");
                    const isAdvanced = !!advBadge || /gemini advanced/i.test(bodyText) || /advanced/i.test(document.title) || /gemini pro/i.test(bodyText);

                    if (isAdvanced) {
                        tier = 'Pro (Advanced)';
                    } else {
                        tier = 'Free (Standard)';
                    }

                    return {
                        email: email || '',
                        name: name || '',
                        tier: tier,
                        isGuest: isGuest,
                        authenticated: !!email && !signInBtn
                    };
                }""")

                if acc_data.get("authenticated") and acc_data.get("email"):
                    result["authenticated"] = True
                    result["account"] = acc_data
                    result["details"] = f"Authenticated as {acc_data['email']} ({acc_data['tier']})"
                    return result
                else:
                    result["authenticated"] = False
                    result["account"] = acc_data
                    result["details"] = "Guest session detected. Google account sign-in required."
                    return result
            except Exception as exc:
                result["details"] = f"Evaluation error: {str(exc)}"

            result["authenticated"] = False
            return result

    except Exception as exc:
        result["details"] = f"Verification error: {str(exc)}"
        return result


async def get_account_info_fast(port: int = DEFAULT_CDP_PORT) -> dict:
    """Extracts the logged-in Google account email, name, and plan tier via CDP."""
    try:
        from playwright.async_api import async_playwright
        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
            for ctx in browser.contexts:
                for page in ctx.pages:
                    if "gemini.google.com" in page.url and "accounts.google.com" not in page.url:
                        info = await page.evaluate("""() => {
                            let email = '';
                            let name = '';
                            let tier = 'Free (Standard)';

                            const accSelectors = [
                                "a[aria-label*='Compte Google']",
                                "a[aria-label*='Google Account']",
                                "button[aria-label*='Compte Google']",
                                "button[aria-label*='Google Account']",
                                "[aria-label*='@']",
                                "a[href*='SignOutOptions']",
                                "a[href*='accounts.google.com']",
                                "button[data-test-id='user-profile-button']",
                                ".gb_A",
                                ".gb_d",
                                ".gb_f",
                                "img[alt*='Photo de profil']",
                                "img[alt*='Profile photo']"
                            ];

                            for (const sel of accSelectors) {
                                const els = document.querySelectorAll(sel);
                                for (const el of els) {
                                    const aria = el.getAttribute('aria-label') || el.getAttribute('title') || el.getAttribute('alt') || '';
                                    const emailMatch = aria.match(/([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,})/);
                                    if (emailMatch && !email) {
                                        email = emailMatch[1];
                                    }
                                    const nameMatch = aria.match(/(?:Compte Google|Google Account)\\s*:\\s*([^(\\n]+)/i);
                                    if (nameMatch && !name) {
                                        name = nameMatch[1].trim();
                                    }
                                }
                            }

                            if (!email) {
                                const allAria = Array.from(document.querySelectorAll('[aria-label]')).map(e => e.getAttribute('aria-label')).join(' ');
                                const m = allAria.match(/([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,})/);
                                if (m) email = m[1];
                            }

                            const bodyText = (document.body ? document.body.innerText : '').slice(0, 3000);
                            const advBadge = document.querySelector("[aria-label*='Advanced'], [aria-label*='Pro'], .subscription-badge, .tier-pill, mat-chip, .sparkle-container");
                            const isAdvanced = !!advBadge || /gemini advanced/i.test(bodyText) || /advanced/i.test(document.title) || /gemini pro/i.test(bodyText);

                            if (isAdvanced) {
                                tier = 'Pro (Advanced)';
                            } else {
                                tier = 'Free (Standard)';
                            }

                            return { email: email || 'Unknown', name: name || 'Unknown', tier: tier };
                        }""")
                        return info
    except Exception:
        pass
    return {"email": "Unknown", "name": "Unknown", "tier": "Free (Standard)"}


async def run_login_flow(chrome_path: str, profile_dir: str, port: int = DEFAULT_CDP_PORT, timeout_sec: int = 300) -> bool:
    """Opens a visible Chrome window directly on Google Login, and automatically closes once signed in."""
    console.print(Panel.fit(
        "[bold cyan]Google Account Sign-In[/bold cyan]\n\n"
        "1. Opening Google sign-in window.\n"
        "2. Sign in or choose your Google account.\n"
        "3. As soon as you log in, this window will automatically\n"
        "   close and GEMINI-CLI-API will connect instantly.",
        border_style="cyan"
    ))

    if is_cdp_ready(port):
        console.print("[dim]Stopping existing process on port 9222...[/dim]")
        stop_chrome(port)
        await asyncio.sleep(1.0)

    console.print("[bold green]Starting visible sign-in window...[/bold green]")
    launch_chrome_process(
        chrome_path=chrome_path,
        profile_dir=profile_dir,
        port=port,
        headless=False,
        url=GOOGLE_LOGIN_URL,
    )

    for _ in range(15):
        if is_cdp_ready(port):
            break
        await asyncio.sleep(0.3)

    if not is_cdp_ready(port):
        console.print("[bold red]Failed to establish CDP connection on port 9222.[/bold red]")
        return False

    console.print("[bold yellow]Please complete Google sign-in in the Chrome window...[/bold yellow]")

    from playwright.async_api import async_playwright

    start_time = time.time()
    try:
        async with async_playwright() as p:
            browser = await p.chromium.connect_over_cdp(f"http://127.0.0.1:{port}")
            while time.time() - start_time < timeout_sec:
                for ctx in browser.contexts:
                    for page in ctx.pages:
                        if "gemini.google.com" in page.url and "accounts.google.com" not in page.url:
                            try:
                                acc = await page.evaluate("""() => {
                                    let email = '';
                                    let name = '';
                                    let tier = 'Free (Standard)';

                                    const accSelectors = [
                                        "a[aria-label*='Compte Google']",
                                        "a[aria-label*='Google Account']",
                                        "button[aria-label*='Compte Google']",
                                        "button[aria-label*='Google Account']",
                                        "[aria-label*='@']",
                                        "a[href*='SignOutOptions']",
                                        "a[href*='accounts.google.com']",
                                        "button[data-test-id='user-profile-button']",
                                        ".gb_A",
                                        ".gb_d",
                                        ".gb_f",
                                        "img[alt*='Photo de profil']",
                                        "img[alt*='Profile photo']"
                                    ];

                                    for (const sel of accSelectors) {
                                        const els = document.querySelectorAll(sel);
                                        for (const el of els) {
                                            const aria = el.getAttribute('aria-label') || el.getAttribute('title') || el.getAttribute('alt') || '';
                                            const emailMatch = aria.match(/([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\\.[a-zA-Z]{2,})/);
                                            if (emailMatch && !email) {
                                                email = emailMatch[1];
                                            }
                                            const nameMatch = aria.match(/(?:Compte Google|Google Account)\\s*:\\s*([^(\\n]+)/i);
                                            if (nameMatch && !name) {
                                                name = nameMatch[1].trim();
                                            }
                                        }
                                    }

                                    const signInBtn = document.querySelector("a[href*='accounts.google.com/ServiceLogin'], a[aria-label*='Se connecter'], a[aria-label*='Sign in'], button[aria-label*='Se connecter'], button[aria-label*='Sign in']");
                                    return {
                                        email: email,
                                        name: name,
                                        authenticated: !!email && !signInBtn
                                    };
                                }""")

                                if acc.get("authenticated") and acc.get("email"):
                                    console.print(f"\n[bold green]Successfully connected as {acc['email']}![/bold green]")
                                    await asyncio.sleep(0.3)
                                    stop_chrome(port)
                                    console.print("[dim]Window closed. Saving session profile...[/dim]\n")
                                    return True
                            except Exception:
                                pass
                await asyncio.sleep(0.4)
    except Exception as exc:
        console.print(f"[red]Monitoring error: {exc}[/red]")

    stop_chrome(port)
    return False


def start_headless_chrome(chrome_path: str, profile_dir: str, port: int = DEFAULT_CDP_PORT, daemon_mode: bool = False) -> bool:
    """Starts Google Chrome in headless=new mode on the designated port."""
    if is_cdp_ready(port):
        console.print(f"[green]Chrome is already running and listening on port {port}.[/green]")
        return True

    console.print("[bold cyan]Starting Google Chrome in headless mode (--headless=new)...[/bold cyan]")
    proc = launch_chrome_process(
        chrome_path=chrome_path,
        profile_dir=profile_dir,
        port=port,
        headless=True,
    )

    for _ in range(20):
        if is_cdp_ready(port):
            console.print(f"[bold green]Headless Chrome is active and listening on port {port}.[/bold green]")
            if not daemon_mode:
                console.print("[dim]Press Ctrl+C to stop headless Chrome.[/dim]")
                try:
                    while True:
                        time.sleep(1)
                except KeyboardInterrupt:
                    console.print("\n[yellow]Stopping headless Chrome...[/yellow]")
                    proc.terminate()
            return True
        time.sleep(0.5)

    console.print("[bold red]Failed to start headless Chrome on port 9222.[/bold red]")
    return False


async def show_status(port: int = DEFAULT_CDP_PORT, profile_dir: str = DEFAULT_PROFILE_DIR):
    """Prints diagnostic table of Chrome CDP and Gemini session status."""
    chrome_path = find_chrome_executable()
    cdp_active = is_cdp_ready(port)

    table = Table(title="Chrome & Gemini Session Status", border_style="cyan", show_header=True)
    table.add_column("Property", style="bold white")
    table.add_column("Value", style="cyan")

    table.add_row("Chrome Executable", chrome_path if chrome_path else "[red]Not found[/red]")
    table.add_row("Profile Directory", profile_dir)
    table.add_row("CDP Port", str(port))
    table.add_row("CDP Connection", "[green]Active (Listening)[/green]" if cdp_active else "[yellow]Inactive[/yellow]")

    if cdp_active:
        auth_status = await check_authentication_status(port)
        auth_text = "[green]Authenticated[/green]" if auth_status["authenticated"] else "[red]Not Authenticated[/red]"
        table.add_row("Gemini Auth Status", auth_text)
        table.add_row("Current Page URL", auth_status["page_url"][:70])
        table.add_row("Status Details", auth_status["details"])

    console.print(table)


def main():
    """Main entrypoint for the authentication and Chrome management tool."""
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    parser = argparse.ArgumentParser(description="Google Gemini Chrome Authentication and Headless Manager")
    parser.add_argument("--login", action="store_true", help="Launch visible Chrome to authenticate your Google account")
    parser.add_argument("--headless", action="store_true", help="Launch Chrome in headless mode (--headless=new)")
    parser.add_argument("--stop", action="store_true", help="Stop running Chrome instance on CDP port")
    parser.add_argument("--status", action="store_true", help="Check Chrome CDP and Gemini session status")
    parser.add_argument("--port", type=int, default=DEFAULT_CDP_PORT, help="CDP port (default: 9222)")
    parser.add_argument("--profile", type=str, default=DEFAULT_PROFILE_DIR, help="Profile directory path")

    args = parser.parse_args()

    chrome_path = find_chrome_executable()
    if not chrome_path:
        console.print("[bold red]Error: Google Chrome executable could not be found on this system.[/bold red]")
        sys.exit(1)

    if args.stop:
        if stop_chrome(args.port):
            console.print(f"[green]Stopped Chrome on port {args.port}.[/green]")
        else:
            console.print(f"[yellow]No Chrome process found on port {args.port}.[/yellow]")
        return

    if args.status:
        asyncio.run(show_status(args.port, args.profile))
        return

    if args.login:
        success = asyncio.run(run_login_flow(chrome_path, args.profile, args.port))
        if success:
            console.print("[bold green]Setup complete. You can now launch headless Chrome or run the API:[/bold green]")
            console.print("  [cyan]python auth.py --headless[/cyan]  (or [cyan]python run.py --headless[/cyan])\n")
        else:
            sys.exit(1)
        return

    if args.headless:
        success = start_headless_chrome(chrome_path, args.profile, args.port)
        if not success:
            sys.exit(1)
        return

    if is_cdp_ready(args.port):
        asyncio.run(show_status(args.port, args.profile))
    else:
        console.print("[yellow]Chrome is not currently running on port 9222.[/yellow]\n")
        console.print("Usage options:")
        console.print("  [cyan]python auth.py --login[/cyan]     Open visible Chrome to authenticate your Google Account")
        console.print("  [cyan]python auth.py --headless[/cyan]  Launch Chrome in background headless mode")
        console.print("  [cyan]python auth.py --status[/cyan]    Check connection and authentication status")
        console.print("  [cyan]python auth.py --stop[/cyan]      Stop running Chrome instances\n")


if __name__ == "__main__":
    main()
