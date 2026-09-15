"""Unit tests for CLI core functionality (stats, completer, client, config)."""

import json
import unittest
from unittest.mock import MagicMock, patch
from prompt_toolkit.document import Document

from cli.config import API_BASE_URL, SLASH_COMMANDS, VERSION
from cli.core.client import APIClient
from cli.core.completer import SlashCommandCompleter
from cli.core.stats import SessionStats


class TestCLICore(unittest.TestCase):
    """Test suite for CLI statistics, completion, and API client."""

    def test_version_and_config(self):
        self.assertIsInstance(VERSION, str)
        self.assertIsInstance(API_BASE_URL, str)
        self.assertIn("/help", SLASH_COMMANDS)
        self.assertIn("/model", SLASH_COMMANDS)
        self.assertIn("/account", SLASH_COMMANDS)
        self.assertIn("/usage", SLASH_COMMANDS)
        self.assertIn("/switch-account", SLASH_COMMANDS)

    def test_session_stats_recording(self):
        stats = SessionStats()
        self.assertEqual(stats.total_prompts, 0)
        self.assertEqual(stats.total_chars_received, 0)

        stats.record_interaction("Prompt 1", "Response 123", 1.5)
        self.assertEqual(stats.total_prompts, 1)
        self.assertEqual(stats.total_generation_time, 1.5)
        self.assertEqual(stats.total_chars_received, len("Response 123"))
        self.assertEqual(len(stats.history_entries), 1)

        stats.record_interaction("Prompt 2", "Another response", 2.5)
        self.assertEqual(stats.total_prompts, 2)
        self.assertEqual(stats.total_generation_time, 4.0)
        self.assertEqual(len(stats.history_entries), 2)

    def test_slash_command_completer(self):
        completer = SlashCommandCompleter()

        # Input: "/m"
        doc = Document(text="/m", cursor_position=2)
        completions = list(completer.get_completions(doc, None))
        completion_texts = [c.text for c in completions]
        self.assertIn("/model", completion_texts)

        # Input: "/ac"
        doc_acc = Document(text="/ac", cursor_position=3)
        completions_acc = list(completer.get_completions(doc_acc, None))
        texts_acc = [c.text for c in completions_acc]
        self.assertIn("/account", texts_acc)

        # Input: "hello" (no slash)
        doc_normal = Document(text="hello", cursor_position=5)
        completions_normal = list(completer.get_completions(doc_normal, None))
        self.assertEqual(len(completions_normal), 0)

    @patch("urllib.request.urlopen")
    def test_api_client_get_status(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "connected": True,
            "gemini_tab_found": True,
        }).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        status = APIClient.get_status()
        self.assertTrue(status["connected"])
        self.assertTrue(status["gemini_tab_found"])

    @patch("urllib.request.urlopen")
    def test_api_client_fetch_models(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "current_model": "pro",
            "models": [{"id": "pro", "name": "Gemini Pro"}],
        }).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        models = APIClient.fetch_models()
        self.assertEqual(models["current_model"], "pro")

    @patch("urllib.request.urlopen")
    def test_api_client_fetch_account(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "email": "user@gmail.com",
            "tier": "Pro (Advanced)",
            "authenticated": True,
        }).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        account = APIClient.fetch_account()
        self.assertEqual(account["email"], "user@gmail.com")
        self.assertEqual(account["tier"], "Pro (Advanced)")


if __name__ == "__main__":
    unittest.main()
