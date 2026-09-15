# Command Guide: GEMINI-API (Chrome CDP Bridge & CLI)

This document contains all essential commands for installation, startup, execution, and testing of the FastAPI backend and interactive CLI connected to Google Gemini via Chrome CDP.

---

## 1. Virtual Environment Management

### Activate Virtual Environment (`.venv`)

#### In PowerShell (Windows):
```powershell
.\.venv\Scripts\Activate.ps1
```

#### In Command Prompt (CMD):
```cmd
.\.venv\Scripts\activate.bat
```

#### In Git Bash / Linux / macOS:
```bash
source .venv/Scripts/activate
```

---

### Update or Reinstall Dependencies

```powershell
.\.venv\Scripts\pip.exe install -r requirements.txt
```

---

## 2. Launching Google Chrome in Remote Debugging Mode (Port 9222)

### Option A: Using the provided PowerShell script
```powershell
.\scripts\launch_chrome.ps1
```

### Option B: Using the provided Batch script (CMD)
```cmd
.\scripts\launch_chrome.bat
```

### Option C: Direct Command Line (CMD / PowerShell)
```cmd
"C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%USERPROFILE%\.chrome_gemini_profile" https://gemini.google.com/app
```

> **Important**: Sign in to your Google Account on Gemini in this Chrome window on the first run. The session profile will be persisted in `%USERPROFILE%\.chrome_gemini_profile`.

---

## 3. Starting the FastAPI Server

### Recommended Launch Command (Windows):
```powershell
.\.venv\Scripts\python.exe run.py
```

> **Windows Note**: Running with standard `uvicorn --reload` under Windows forces a `Selector` event loop incompatible with Playwright subprocesses. The `run.py` entrypoint configures `ProactorEventLoop` cleanly without conflicts.

---

## 4. API Documentation & Web UI

- **Swagger UI (Interactive API Docs)**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc (Alternative Docs)**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 5. Interactive CLI Interface

A rich terminal interface with auto-completion, persistent command history, real-time streaming preview, structured Markdown rendering, and code syntax highlighting.

### Start the CLI:
```powershell
.\.venv\Scripts\python.exe cli.py
```

### Features:
- **Intelligent Auto-completion**: Type `/` and press `Tab` to navigate through slash commands.
- **Persistent History**: Use `Up` and `Down` arrow keys to browse previous prompts across sessions.
- **Live Markdown Rendering**: Code blocks (Python, JS, Bash, etc.), tables, lists, and bold text are cleanly formatted.
- **Session Metrics**: Live tracking of elapsed generation time, character count, and average speed.

### Available Slash (`/`) Commands:
| Command | Description |
| :--- | :--- |
| `/model [name]` | Interactive arrow-key selector or direct switch (`pro`, `flash`, `flash-lite`, `thinking`) |
| `/usage` | View current and weekly quota limits, plan tier (e.g., PRO), and reset schedules |
| `/convs` | List saved conversations from Gemini sidebar history |
| `/load [id]` | Interactive selector or direct resumption of a previous chat |
| `/new [prompt]` | Start a fresh new chat session on Gemini (or send prompt directly in new chat) |
| `/status` | Diagnostic table for FastAPI server, Chrome CDP port, and active Gemini tab |
| `/stream` | Toggle between real-time streaming preview and standard sync mode |
| `/save [file.md]` | Export active conversation history to a Markdown file |
| `/stats` | Display session performance metrics and summary |
| `/history` | Show recent prompt history |
| `/config` | Display active API configuration |
| `/clear` | Clear terminal screen |
| `/help` | Show command help menu |
| `/exit` | Display session summary and exit application |

---


## 6. API Test Commands (cURL)

### 6.1 Check General Server Health
```bash
curl -X GET http://127.0.0.1:8000/health
```

---

### 6.2 Check Chrome CDP Connection and Gemini Tab
```bash
curl -X GET http://127.0.0.1:8000/cdp/status
```

---

### 6.3 Send a Simple Prompt (Full JSON Response)

#### In Bash / Git Bash / Linux:
```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Explain the theory of relativity in 3 sentences."}'
```

#### In PowerShell:
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/chat" -Method Post -ContentType "application/json" -Body '{"prompt": "Explain the theory of relativity in 3 sentences."}'
```

#### In Windows CMD (`curl.exe`):
```cmd
curl.exe -X POST http://127.0.0.1:8000/chat -H "Content-Type: application/json" -d "{\"prompt\": \"Explain the theory of relativity in 3 sentences.\"}"
```

---

### 6.4 Reset Session Manually (Start New Chat)
```bash
curl -X POST http://127.0.0.1:8000/chat/new
```

---

### 6.5 Send Prompt with Direct New Chat Creation (`new_chat: true`)
```bash
curl -X POST http://127.0.0.1:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Start a new session and summarize Python functions.", "new_chat": true}'
```

---

### 6.6 Send Prompt with Real-Time SSE Streaming
```bash
curl -N -X POST http://127.0.0.1:8000/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Write a short poem about the ocean."}'
```

---

### 6.7 Language Model Selection

#### List available models and active model:
```bash
curl -X GET http://127.0.0.1:8000/models
```

#### Switch active model:
```bash
curl -X POST http://127.0.0.1:8000/models/select \
  -H "Content-Type: application/json" \
  -d '{"model": "pro"}'
```

---

### 6.8 Conversation History

#### List previous chats:
```bash
curl -X GET http://127.0.0.1:8000/conversations
```

#### Resume a previous chat by ID:
```bash
curl -X POST http://127.0.0.1:8000/conversations/<id>/load
```

---

### 6.9 Quotas and Usage Limits

#### Get plan tier and current / weekly usage metrics:
```bash
curl -X GET http://127.0.0.1:8000/usage
```

---

### 6.10 OpenAI Compatible Endpoint (`/v1/chat/completions`)

#### Standard Mode:
```bash
curl -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-web",
    "messages": [
      {"role": "system", "content": "You are an expert software engineer."},
      {"role": "user", "content": "What is the distance between the Earth and Moon?"}
    ]
  }'
```

#### Streaming Mode:
```bash
curl -N -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-web",
    "messages": [
      {"role": "user", "content": "List 5 facts about the human brain."}
    ],
    "stream": true
  }'
```

---

## 7. Client Code Examples

### Python (`httpx`)

```python
import httpx

# 1. Synchronous request
response = httpx.post(
    "http://127.0.0.1:8000/chat",
    json={"prompt": "Hello Gemini, how are you?"},
    timeout=120.0,
)
print("Response:", response.json()["response"])

# 2. SSE Streaming
with httpx.stream(
    "POST",
    "http://127.0.0.1:8000/chat/stream",
    json={"prompt": "Tell me a short joke."},
    timeout=120.0,
) as r:
    for line in r.iter_lines():
        if line:
            print(line)
```

---

### Official OpenAI Python SDK

```python
from openai import OpenAI

client = OpenAI(
    base_url="http://127.0.0.1:8000/v1",
    api_key="none",  # No API key required
)

# Standard call
completion = client.chat.completions.create(
    model="gemini-web",
    messages=[
        {"role": "user", "content": "Give me 3 productivity tips."}
    ],
)
print(completion.choices[0].message.content)

# Streaming call
stream = client.chat.completions.create(
    model="gemini-web",
    messages=[
        {"role": "user", "content": "Write a haiku about nature."}
    ],
    stream=True,
)
for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="", flush=True)
```

---

### JavaScript / Node.js (`fetch`)

```javascript
async function askGemini(prompt) {
  const res = await fetch("http://127.0.0.1:8000/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ prompt }),
  });
  const data = await res.json();
  console.log("Response:", data.response);
}

askGemini("What are the core benefits of FastAPI?");
```

