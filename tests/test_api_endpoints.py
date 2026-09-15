"""Unit tests for FastAPI endpoints and router integrations."""

import unittest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from app.dependencies import get_cdp_manager, get_gemini_driver
from app.main import app
from app.schemas import ModelInfo


class TestAPIEndpoints(unittest.TestCase):
    """Test suite for FastAPI REST and SSE endpoints."""

    def setUp(self):
        self.mock_driver = MagicMock()
        self.mock_cdp = MagicMock()

        # Wire dependency overrides
        app.dependency_overrides[get_gemini_driver] = lambda: self.mock_driver
        app.dependency_overrides[get_cdp_manager] = lambda: self.mock_cdp
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_root_endpoint(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("message", data)
        self.assertEqual(data["documentation"], "/docs")

    def test_health_check(self):
        from app.config import settings
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["app_name"], settings.APP_NAME)

    def test_cdp_status_connected(self):
        self.mock_cdp.check_status = AsyncMock(return_value={
            "connected": True,
            "cdp_url": "http://127.0.0.1:9222",
            "gemini_tab_found": True,
            "page_title": "Google Gemini",
            "url": "https://gemini.google.com/app",
            "details": "Operating normally",
        })

        resp = self.client.get("/cdp/status")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["connected"])
        self.assertTrue(data["gemini_tab_found"])

    def test_list_models(self):
        self.mock_driver.get_available_models = AsyncMock(return_value={
            "current_model": "pro",
            "models": [
                {"id": "pro", "name": "Gemini 2.5 Pro", "is_active": True},
                {"id": "flash", "name": "Gemini 2.5 Flash", "is_active": False},
            ],
        })

        resp = self.client.get("/models")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["current_model"], "pro")
        self.assertEqual(len(data["models"]), 2)

    def test_select_model(self):
        self.mock_driver.set_model = AsyncMock(return_value={
            "status": "success",
            "current_model": "flash",
            "message": "Switched to 2.5 Flash",
        })

        resp = self.client.post("/models/select", json={"model": "flash"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")
        self.assertEqual(data["current_model"], "flash")

    def test_list_conversations(self):
        self.mock_driver.list_conversations = AsyncMock(return_value=[
            {"id": "c1", "title": "Chat 1", "url": "https://gemini.google.com/app/c1"},
            {"id": "c2", "title": "Chat 2", "url": "https://gemini.google.com/app/c2"},
        ])

        resp = self.client.get("/conversations")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["total"], 2)
        self.assertEqual(len(data["conversations"]), 2)

    def test_load_conversation(self):
        self.mock_driver.load_conversation = AsyncMock(return_value={
            "status": "success",
            "conversation_id": "c1",
            "title": "Chat 1",
            "url": "https://gemini.google.com/app/c1",
            "message": "Conversation loaded",
        })

        resp = self.client.post("/conversations/c1/load")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["conversation_id"], "c1")
        self.assertEqual(data["title"], "Chat 1")

    def test_get_usage_metrics(self):
        self.mock_driver.get_usage_metrics = AsyncMock(return_value={
            "tier": "PRO",
            "current_usage": "10 % used",
            "current_percent": 10.0,
            "current_reset_time": "in 2 hours",
            "weekly_usage": "40 % used",
            "weekly_percent": 40.0,
            "weekly_reset_time": "in 4 days",
            "description": "Pro plan limits",
        })

        resp = self.client.get("/usage")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["tier"], "PRO")
        self.assertEqual(data["current_percent"], 10.0)

    def test_get_account_info(self):
        self.mock_driver.get_account_info = AsyncMock(return_value={
            "email": "developer@example.com",
            "name": "Dev User",
            "tier": "Pro (Advanced)",
            "authenticated": True,
        })

        resp = self.client.get("/account")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["email"], "developer@example.com")
        self.assertEqual(data["tier"], "Pro (Advanced)")
        self.assertTrue(data["authenticated"])

    def test_start_new_chat(self):
        self.mock_driver.reset_session = AsyncMock(return_value=None)
        resp = self.client.post("/chat/new")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "success")

    def test_send_chat_prompt_success(self):
        self.mock_driver.send_prompt = AsyncMock(return_value="Python is a programming language.")

        resp = self.client.post("/chat", json={"prompt": "What is Python?"})
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["response"], "Python is a programming language.")
        self.assertEqual(data["status"], "success")
        self.assertGreaterEqual(data["duration_seconds"], 0)

    def test_send_chat_prompt_connection_error(self):
        self.mock_driver.send_prompt = AsyncMock(side_effect=ConnectionError("CDP disconnected"))

        resp = self.client.post("/chat", json={"prompt": "Hello"})
        self.assertEqual(resp.status_code, 503)

    def test_send_chat_prompt_timeout_error(self):
        self.mock_driver.send_prompt = AsyncMock(side_effect=TimeoutError("Response timeout"))

        resp = self.client.post("/chat", json={"prompt": "Hello"})
        self.assertEqual(resp.status_code, 504)

    def test_openai_chat_completions(self):
        self.mock_driver.send_prompt = AsyncMock(return_value="OpenAI compatible response.")

        payload = {
            "model": "gemini-web",
            "messages": [{"role": "user", "content": "Hello"}],
            "stream": False,
        }
        resp = self.client.post("/v1/chat/completions", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["object"], "chat.completion")
        self.assertEqual(data["choices"][0]["message"]["content"], "OpenAI compatible response.")


if __name__ == "__main__":
    unittest.main()
