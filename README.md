# GEMINI-CLI-API: Gemini Chrome CDP Bridge & CLI

A local high-performance API and interactive terminal CLI built with **FastAPI** and **Playwright**, enabling you to drive an existing authenticated **Google Gemini Web** session in Google Chrome via the **Chrome DevTools Protocol (CDP)** on port `9222`.

---

## Features

- **Bypass Captchas & Cloudflare**: Uses your existing signed-in Google Chrome session directly.
- **Non-intrusive CDP Connection**: Connects to Chrome port `9222` without launching a blank or headless browser.
- **Full Model Support**: Switch seamlessly between `3.1 Pro`, `3.8 Flash`, `3.5 Flash-Lite`, and `Extended Thinking`.
- **Usage & Quotas Dashboard**: Inspect daily and weekly quota limits, reset times, and plan tiers (`/usage`).
- **Chat History & Resumption**: Browse and resume past conversations directly from the sidebar (`/convs`, `/load`).
- **Synchronous & Real-Time Streaming**:
  - `POST /chat`: Full structured markdown response after generation completes.
  - `POST /chat/stream`: Real-time streaming via Server-Sent Events (SSE).
  - `POST /v1/chat/completions`: Standard OpenAI Chat Completions compatibility (works with LibreChat, Open WebUI, etc.).
- **Rich Interactive CLI**: Terminal interface with auto-completion, model selection, live Markdown rendering, prompt history, and session metrics.

---

## Installation

### Prerequisites
- Python 3.10+
- Google Chrome installed

### Step 1: Create Virtual Environment and Install
```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Install in editable mode to enable the global CLI command
pip install -e .
```

---

## Quick Start Guide

### Launching the Application

You can launch using the dedicated CLI command or python:
```powershell
gemini-cli-api
```
*(or `python run.py`)*

`run.py` automatically manages the entire lifecycle:
1. **Virtual Environment**: Auto-detects and uses `.venv` without needing manual activation.
2. **Session Verification**: Checks if your Google Gemini session is active in `~/.chrome_gemini_profile`.
   - If not signed in, it displays a sign-in notification and opens Google Chrome to `https://gemini.google.com/app`. Once you log in, it detects your session, saves your profile, and closes the window.
3. **Headless Engine**: Google Chrome is launched in modern `--headless=new` mode in the background on port `9222`.
4. **Interactive Mode Selector**: Displays an interactive menu to choose your preferred mode:
   - **`Both (API Server + Interactive CLI)`**: Starts the FastAPI server in the background and opens the interactive terminal CLI.
   - **`Interactive CLI Only`**: Runs background API engine and starts the terminal CLI REPL directly.
   - **`API Server Only`**: Runs FastAPI in the foreground on `http://127.0.0.1:8000` with Swagger UI at `http://127.0.0.1:8000/docs`.

### Direct Command Flags (Optional)

You can also bypass the menu directly via flags:
```powershell
gemini-cli-api --both     # Start background API + Interactive CLI
gemini-cli-api --cli      # Start Interactive CLI directly
gemini-cli-api --api      # Start Foreground API Server (http://127.0.0.1:8000)
gemini-cli-api --logout   # Terminate Chrome, delete local session profile, and log out
```

---

### Authentication & Headless Management Tool (`auth.py`)

A dedicated utility for managing browser authentication and headless processes:
```powershell
python auth.py --login      # Interactive 1-time Google account login
python auth.py --status     # Check Chrome CDP and Gemini session status
python auth.py --headless   # Start headless Chrome supervisor
python auth.py --stop       # Terminate running Chrome instances on port 9222
```

---

## CLI Slash Commands

| Command | Description |
| :--- | :--- |
| `/model [name]` | Interactive arrow-key selector or direct model switch (`pro`, `flash`, `flash-lite`, `thinking`) |
| `/account` | Display connected Google account email, name, and plan tier (`Pro (Advanced)` / `Free (Standard)`) |
| `/switch-account` | Switch Google Account (logs out and opens visible sign-in window) |
| `/usage` | View current and weekly quota limits and reset schedules |
| `/convs` | List previous saved conversations from Gemini history |
| `/load [id]` | Interactive selector or direct resumption of a previous chat |
| `/new [prompt]` | Start a fresh new conversation on Gemini (or send prompt directly) |
| `/status` | Diagnostic table for FastAPI, Chrome CDP, and Gemini tab |
| `/stream` | Toggle between real-time streaming and sync mode |
| `/save [file.md]` | Export conversation history to Markdown |
| `/stats` | Display session metrics and performance |
| `/history` | Show recent prompt history |
| `/config` | Display active configuration |
| `/clear` | Clear terminal screen |
| `/help` | Show command help menu |
| `/exit` | Exit session with metrics summary |

---

## Automated Test Suite

A complete test suite is available under `tests/` to verify schemas, API endpoints, authentication, and CLI components:

```bash
# Run the test suite with formatted output
python tests/runner.py

# Or run via Python unittest
python -m unittest discover tests
```

---

## API Usage Examples

### 1. Check CDP Connection Status
```bash
curl -X GET http://127.0.0.1:8000/cdp/status
```

### 2. Send Prompt (Synchronous JSON)
```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d "{\"prompt\": \"Explain quantum computing in 3 concise bullet points.\"}"
```

### 3. Send Prompt (Real-Time SSE Streaming)
```bash
curl -N -X POST http://127.0.0.1:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d "{\"prompt\": \"Write a short poem about coding.\"}"
```

### 4. OpenAI Format Compatibility
```bash
curl -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-web",
    "messages": [
      {"role": "user", "content": "What is the capital of Australia?"}
    ]
  }'
```

---

## Project Structure

```text
gemini-cli-api/
├── app/                     # Backend FastAPI application
│   ├── __init__.py
│   ├── main.py              # FastAPI application and lifespan management
│   ├── config.py            # Settings and DOM selectors
│   ├── schemas.py           # Pydantic schemas for request/response validation
│   ├── dependencies.py      # Dependency injection providers
│   ├── services/
│   │   ├── __init__.py
│   │   ├── cdp_manager.py   # Chrome DevTools Protocol Playwright manager
│   │   └── gemini_driver.py # Gemini DOM manipulation and response extraction
│   └── routers/
│       ├── __init__.py
│       ├── chat.py          # /chat, /chat/stream, /models, /conversations, /usage, /account
│       └── health.py        # /health, /cdp/status
├── cli/                     # Modular interactive terminal CLI package
│   ├── __init__.py
│   ├── config.py            # CLI constants, theme styles, command list
│   ├── main.py              # Main REPL execution loop and command dispatcher
│   ├── core/                # Core business logic and networking
│   │   ├── __init__.py
│   │   ├── client.py        # REST HTTP API client for backend communications
│   │   ├── completer.py     # Prompt auto-completion engine
│   │   └── stats.py         # Session statistics and latency tracker
│   ├── ui/                  # Rich terminal UI components
│   │   ├── __init__.py
│   │   ├── banners.py       # ASCII art header, quick status card, dynamic box borders
│   │   ├── menus.py         # Arrow-key navigable selection menus
│   │   ├── panels.py        # Markdown response and notification panels
│   │   └── tables.py        # Help, diagnostic status, and history tables
│   └── handlers/            # Slash command handlers
│       ├── __init__.py
│       ├── chat.py          # Real-time streaming and sync messaging routines
│       ├── conversations.py # History listing and chat resumption
│       ├── models.py        # Model selector and switcher (/model)
│       └── usage.py         # Account quotas and Google account info (/usage, /account)
├── scripts/
│   ├── launch_chrome.bat    # Windows Batch script to start Chrome on port 9222
│   └── launch_chrome.ps1    # PowerShell script to start Chrome on port 9222
├── tests/                   # Automated unit test suite
│   ├── __init__.py
│   ├── test_schemas.py      # Pydantic schema validation tests
│   ├── test_api_endpoints.py# FastAPI REST endpoint integration tests
│   ├── test_auth_and_cdp.py # CDP connection and auth workflow tests
│   ├── test_cli_core.py     # CLI statistics, completion, client tests
│   ├── test_cli_ui.py       # CLI UI table, banner, panel tests
│   └── runner.py            # Rich test runner & summary reporter
├── auth.py                  # Standalone authentication & headless Chrome manager
├── cli.py                   # Main CLI entrypoint script
├── run.py                   # Unified orchestrator (auto-auth, headless, mode selection)
├── pyproject.toml           # PEP 621 package and scripts configuration
├── requirements.txt         # Python dependencies
└── README.md                # Documentation
```