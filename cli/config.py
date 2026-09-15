"""Configuration and constants for the GEMINI-API CLI."""

import os
from prompt_toolkit.styles import Style as PTStyle
from rich.console import Console

API_BASE_URL = os.getenv("API_URL", "http://127.0.0.1:8000")
HISTORY_FILE = os.path.expanduser("~/.gemini_cli_history")
VERSION = "1.1.0"

console = Console()

SLASH_COMMANDS = [
    "/help",
    "/model",
    "/usage",
    "/convs",
    "/load",
    "/new",
    "/status",
    "/stream",
    "/save",
    "/stats",
    "/history",
    "/config",
    "/clear",
    "/exit",
]


pt_style = PTStyle.from_dict({
    "prompt_bracket": "ansibrightblack",
    "prompt_tag": "ansicyan bold",
    "prompt_arrow": "ansigreen bold",
    "prompt_border": "ansibrightblack",
    "prompt": "ansicyan bold",
})

