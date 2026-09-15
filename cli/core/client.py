"""HTTP Client for communicating with the Gemini CDP Bridge API."""

import json
import urllib.error
import urllib.request
from typing import Any, Optional
from cli.config import API_BASE_URL


class APIClient:
    """Encapsulates all REST calls to the backend."""

    @staticmethod
    def get_status() -> dict[str, Any]:
        """Fetches CDP bridge diagnostic status."""
        url = f"{API_BASE_URL}/cdp/status"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def get_quick_status() -> tuple[bool, str]:
        """Quickly checks connection state and active model."""
        try:
            data = APIClient.get_status()
            connected = data.get("connected", False)
            tab_found = data.get("gemini_tab_found", False)
            return (connected and tab_found, "Flash")
        except Exception:
            return (False, "Unknown")

    @staticmethod
    def reset_chat() -> bool:
        """Sends request to reset Gemini session."""
        try:
            url = f"{API_BASE_URL}/chat/new"
            req = urllib.request.Request(url, data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
            with urllib.request.urlopen(req, timeout=10) as response:
                return response.status == 200
        except Exception:
            return False

    @staticmethod
    def fetch_models() -> dict[str, Any]:
        """Fetches supported models and the currently selected one."""
        url = f"{API_BASE_URL}/models"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=5) as response:
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def switch_model(target_model: str) -> dict[str, Any]:
        """Switches the active language model."""
        url = f"{API_BASE_URL}/models/select"
        payload = {"model": target_model}
        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data_bytes,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def fetch_conversations() -> list[dict[str, Any]]:
        """Fetches conversation history from Gemini."""
        url = f"{API_BASE_URL}/conversations"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=8) as response:
            data = json.loads(response.read().decode("utf-8"))
            return data.get("conversations", [])

    @staticmethod
    def load_conversation(conversation_id: str) -> dict[str, Any]:
        """Loads a previous conversation into the active session."""
        url = f"{API_BASE_URL}/conversations/{conversation_id}/load"
        req = urllib.request.Request(url, data=b"{}", headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))

    @staticmethod
    def fetch_usage() -> dict[str, Any]:
        """Fetches usage quotas and reset schedules."""
        url = f"{API_BASE_URL}/usage"
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
