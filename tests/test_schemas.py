"""Unit tests for Pydantic data schemas."""

import unittest
from datetime import datetime
from pydantic import ValidationError

from app.schemas import (
    AccountInfoResponse,
    CDPStatusResponse,
    ChatResponse,
    ConversationInfo,
    ConversationsResponse,
    ConversationSelectResponse,
    HealthResponse,
    ModelInfo,
    ModelsResponse,
    ModelSelectRequest,
    ModelSelectResponse,
    OpenAIChatChoice,
    OpenAIChatChoiceMessage,
    OpenAIChatCompletionRequest,
    OpenAIChatCompletionResponse,
    OpenAIChatMessage,
    PromptRequest,
    UsageMetricsResponse,
)


class TestSchemas(unittest.TestCase):
    """Test suite for all API request and response schemas."""

    def test_prompt_request_valid(self):
        req = PromptRequest(prompt="Hello Gemini", new_chat=True, timeout_seconds=60, model="pro")
        self.assertEqual(req.prompt, "Hello Gemini")
        self.assertTrue(req.new_chat)
        self.assertEqual(req.timeout_seconds, 60)
        self.assertEqual(req.model, "pro")

    def test_prompt_request_defaults(self):
        req = PromptRequest(prompt="Test prompt")
        self.assertEqual(req.prompt, "Test prompt")
        self.assertFalse(req.new_chat)
        self.assertIsNone(req.timeout_seconds)
        self.assertIsNone(req.model)

    def test_prompt_request_validation_errors(self):
        with self.assertRaises(ValidationError):
            PromptRequest(prompt="")  # min_length=1
        with self.assertRaises(ValidationError):
            PromptRequest(prompt="Valid", timeout_seconds=2)  # ge=5
        with self.assertRaises(ValidationError):
            PromptRequest(prompt="Valid", timeout_seconds=1000)  # le=600

    def test_model_info_and_models_response(self):
        m1 = ModelInfo(id="pro", name="Gemini 2.5 Pro", is_active=True)
        m2 = ModelInfo(id="flash", name="Gemini 2.5 Flash", is_active=False)
        resp = ModelsResponse(current_model="pro", models=[m1, m2])
        self.assertEqual(resp.current_model, "pro")
        self.assertEqual(len(resp.models), 2)
        self.assertTrue(resp.models[0].is_active)

    def test_model_select_request_and_response(self):
        req = ModelSelectRequest(model="flash")
        self.assertEqual(req.model, "flash")

        resp = ModelSelectResponse(status="success", current_model="flash", message="Switched to flash")
        self.assertEqual(resp.status, "success")
        self.assertEqual(resp.current_model, "flash")

    def test_conversation_info_and_responses(self):
        c1 = ConversationInfo(id="conv-123", title="AI Chat", url="https://gemini.google.com/app/conv-123")
        self.assertEqual(c1.id, "conv-123")
        self.assertEqual(c1.title, "AI Chat")

        resp = ConversationsResponse(total=1, conversations=[c1])
        self.assertEqual(resp.total, 1)
        self.assertEqual(len(resp.conversations), 1)

        sel_resp = ConversationSelectResponse(
            status="success",
            conversation_id="conv-123",
            title="AI Chat",
            url="https://gemini.google.com/app/conv-123",
            message="Loaded",
        )
        self.assertEqual(sel_resp.conversation_id, "conv-123")

    def test_usage_metrics_response(self):
        usage = UsageMetricsResponse(
            tier="PRO",
            current_usage="5 % used",
            current_percent=5.0,
            current_reset_time="in 4 hours",
            weekly_usage="20 % used",
            weekly_percent=20.0,
            weekly_reset_time="in 3 days",
            description="Gemini Advanced Plan",
        )
        self.assertEqual(usage.tier, "PRO")
        self.assertEqual(usage.current_percent, 5.0)
        self.assertEqual(usage.weekly_percent, 20.0)

    def test_chat_response(self):
        chat = ChatResponse(response="Hello from Gemini!", duration_seconds=1.23, status="success")
        self.assertEqual(chat.response, "Hello from Gemini!")
        self.assertEqual(chat.duration_seconds, 1.23)
        self.assertEqual(chat.status, "success")
        self.assertIsInstance(chat.created_at, datetime)

    def test_openai_compatibility_schemas(self):
        msg = OpenAIChatMessage(role="user", content="Explain quantum physics")
        self.assertEqual(msg.role, "user")
        self.assertEqual(msg.content, "Explain quantum physics")

        req = OpenAIChatCompletionRequest(
            model="gemini-web",
            messages=[msg],
            stream=False,
            temperature=0.7,
        )
        self.assertEqual(req.model, "gemini-web")
        self.assertFalse(req.stream)

        resp = OpenAIChatCompletionResponse(
            id="chatcmpl-test",
            created=1234567890,
            choices=[
                OpenAIChatChoice(
                    index=0,
                    message=OpenAIChatChoiceMessage(role="assistant", content="Quantum physics is..."),
                    finish_reason="stop",
                )
            ],
        )
        self.assertEqual(resp.id, "chatcmpl-test")
        self.assertEqual(resp.choices[0].message.content, "Quantum physics is...")

    def test_cdp_status_response(self):
        status = CDPStatusResponse(
            connected=True,
            cdp_url="http://127.0.0.1:9222",
            gemini_tab_found=True,
            page_title="Google Gemini",
            url="https://gemini.google.com/app",
            details="Operating normally",
        )
        self.assertTrue(status.connected)
        self.assertTrue(status.gemini_tab_found)
        self.assertEqual(status.cdp_url, "http://127.0.0.1:9222")

    def test_health_response(self):
        health = HealthResponse(status="ok", app_name="GEMINI-CLI-API", version="1.1.0")
        self.assertEqual(health.status, "ok")
        self.assertEqual(health.app_name, "GEMINI-CLI-API")
        self.assertEqual(health.version, "1.1.0")

    def test_account_info_response(self):
        acc = AccountInfoResponse(
            email="testuser@gmail.com",
            name="Test User",
            tier="Pro (Advanced)",
            authenticated=True,
        )
        self.assertEqual(acc.email, "testuser@gmail.com")
        self.assertEqual(acc.name, "Test User")
        self.assertEqual(acc.tier, "Pro (Advanced)")
        self.assertTrue(acc.authenticated)

        acc_default = AccountInfoResponse()
        self.assertEqual(acc_default.email, "Unknown")
        self.assertEqual(acc_default.tier, "Free (Standard)")
        self.assertFalse(acc_default.authenticated)


if __name__ == "__main__":
    unittest.main()
