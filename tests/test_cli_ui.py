"""Unit tests for CLI UI tables, banners, and panels."""

import unittest
from unittest.mock import MagicMock, patch

from cli.core.stats import SessionStats
from cli.handlers.conversations import handle_conversations
from cli.handlers.usage import handle_account, handle_usage
from cli.ui.banners import (
    get_terminal_width,
    print_banner,
    print_prompt_box_bottom,
    print_prompt_box_top,
)
from cli.ui.panels import render_error_panel, render_exit_panel, render_response_panel
from cli.ui.tables import (
    render_config_table,
    render_help_table,
    render_history_table,
    render_status_table,
)


class TestCLIUI(unittest.TestCase):
    """Test suite for Rich CLI UI elements."""

    def test_get_terminal_width(self):
        width = get_terminal_width()
        self.assertIsInstance(width, int)
        self.assertGreaterEqual(width, 10)

    @patch("cli.ui.banners.console.print")
    def test_print_banner_disconnected(self, mock_print):
        print_banner(connected=False)
        self.assertTrue(mock_print.called)

    @patch("cli.ui.banners.console.print")
    def test_print_banner_connected_with_account(self, mock_print):
        acc = {
            "email": "test@example.com",
            "tier": "Pro (Advanced)",
            "authenticated": True,
        }
        print_banner(connected=True, account_info=acc)
        self.assertTrue(mock_print.called)

    @patch("cli.ui.banners.console.print")
    def test_print_prompt_boxes(self, mock_print):
        print_prompt_box_top(tag="Question")
        print_prompt_box_bottom()
        self.assertEqual(mock_print.call_count, 2)

    @patch("cli.ui.tables.console.print")
    def test_render_help_table(self, mock_print):
        render_help_table()
        self.assertTrue(mock_print.called)

    @patch("cli.ui.tables.console.print")
    def test_render_status_table(self, mock_print):
        status_data = {
            "connected": True,
            "gemini_tab_found": True,
            "cdp_url": "http://127.0.0.1:9222",
            "page_title": "Google Gemini",
            "url": "https://gemini.google.com/app",
            "details": "Ready",
        }
        render_status_table(status_data)
        self.assertTrue(mock_print.called)

    @patch("cli.ui.tables.console.print")
    def test_render_history_table(self, mock_print):
        history = [
            {"timestamp": "2026-09-15 20:00:00", "prompt": "Test Q", "response": "Test A", "duration": 1.2},
        ]
        render_history_table(history)
        self.assertTrue(mock_print.called)

        # Empty history
        render_history_table([])
        self.assertTrue(mock_print.called)

    @patch("cli.ui.tables.console.print")
    def test_render_config_table(self, mock_print):
        render_config_table(streaming_mode=True)
        render_config_table(streaming_mode=False)
        self.assertTrue(mock_print.called)

    @patch("cli.ui.panels.console.print")
    def test_render_panels(self, mock_print):
        stats = SessionStats()
        render_exit_panel(stats)
        render_response_panel("This is a test response", 1.23)
        render_error_panel("This is an error notification")
        self.assertTrue(mock_print.called)

    @patch("cli.core.client.APIClient.fetch_usage")
    @patch("cli.config.console.print")
    def test_handle_usage_ui(self, mock_print, mock_fetch):
        mock_fetch.return_value = {
            "tier": "PRO",
            "current_usage": "10 % used",
            "current_percent": 10.0,
            "current_reset_time": "in 2 hours",
            "weekly_usage": "35 % used",
            "weekly_percent": 35.0,
            "weekly_reset_time": "in 3 days",
        }
        handle_usage()
        self.assertTrue(mock_print.called)

    @patch("cli.core.client.APIClient.fetch_account")
    @patch("cli.config.console.print")
    def test_handle_account_ui(self, mock_print, mock_fetch):
        mock_fetch.return_value = {
            "email": "user@gmail.com",
            "name": "User Name",
            "tier": "Pro (Advanced)",
            "authenticated": True,
        }
        handle_account()
        self.assertTrue(mock_print.called)

    @patch("cli.core.client.APIClient.fetch_conversations")
    @patch("cli.config.console.print")
    def test_handle_conversations_ui(self, mock_print, mock_fetch):
        mock_fetch.return_value = [
            {"id": "conv-1", "title": "Chat 1", "url": "https://gemini.google.com/app/conv-1"},
            {"id": "conv-2", "title": "Chat 2", "url": "https://gemini.google.com/app/conv-2"},
        ]
        convs = handle_conversations()
        self.assertEqual(len(convs), 2)
        self.assertTrue(mock_print.called)


if __name__ == "__main__":
    unittest.main()
