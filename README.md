# GEMINI-API: Gemini Chrome CDP Bridge & CLI

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

### Step 1: Create Virtual Environment and Install Dependencies

```bash
# Create virtual environment
python -m venv .venv

# Activate (Windows PowerShell)
.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

---

## Quick Start Guide

### Step 1: Launch Chrome with Remote Debugging

#### Option A: Using the provided script
Double-click `scripts\launch_chrome.bat` or run in PowerShell:
```powershell
.\scripts\launch_chrome.ps1
```

#### Option B: Manual command line
```cmd
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%USERPROFILE%\.chrome_gemini_profile" https://gemini.google.com/app
```

> **Note**: Log in to your Google Account on Gemini in this Chrome window. The profile is saved in `.chrome_gemini_profile`.

---

### Step 2: Start the FastAPI Server

```powershell
.\.venv\Scripts\python.exe run.py
```

Interactive Swagger documentation is available at: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

---

### Step 3: Launch the Interactive CLI

In a separate terminal:
```powershell
.\.venv\Scripts\python.exe cli.py
```

---

## CLI Slash Commands

| Command | Description |
| :--- | :--- |
| `/model [name]` | Interactive arrow-key selector or direct model switch (`pro`, `flash`, `flash-lite`, `thinking`) |
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
geminiapi/
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
│       ├── chat.py          # /chat, /chat/stream, /models, /conversations, /usage
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
│       └── usage.py         # Account quotas and reset limits (/usage)
├── scripts/
│   ├── launch_chrome.bat    # Windows Batch script to start Chrome on port 9222
│   └── launch_chrome.ps1    # PowerShell script to start Chrome on port 9222
├── cli.py                   # Main CLI entrypoint script
├── run.py                   # Server entrypoint with Windows Proactor loop support
├── test_api.py              # Automated API verification test suite
├── requirements.txt         # Python dependencies
└── README.md                # Documentation
```