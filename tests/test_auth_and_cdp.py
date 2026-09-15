"""Unit tests for Chrome DevTools Protocol management and authentication utilities."""

import json
import unittest
from unittest.mock import MagicMock, patch

import auth
from auth import (
    DEFAULT_CDP_PORT,
    DEFAULT_PROFILE_DIR,
    GEMINI_URL,
    GOOGLE_LOGIN_URL,
    check_auth_fast,
    find_chrome_executable,
    get_cdp_tabs,
    is_cdp_ready,
)


class TestAuthAndCDP(unittest.TestCase):
    """Test suite for Chrome authentication and CDP manager."""

    def test_constants(self):
        self.assertEqual(DEFAULT_CDP_PORT, 9222)
        self.assertIn(".chrome_gemini_profile", DEFAULT_PROFILE_DIR)
        self.assertIn("gemini.google.com", GEMINI_URL)
        self.assertIn("accounts.google.com", GOOGLE_LOGIN_URL)

    def test_find_chrome_executable(self):
        # Should return a string or None depending on system
        path = find_chrome_executable()
        if path is not None:
            self.assertIsInstance(path, str)
            self.assertGreater(len(path), 0)

    @patch("urllib.request.urlopen")
    def test_is_cdp_ready_true(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({"webSocketDebuggerUrl": "ws://127.0.0.1:9222/devtools/browser"}).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        ready = is_cdp_ready(9222)
        self.assertTrue(ready)

    @patch("urllib.request.urlopen")
    def test_is_cdp_ready_false(self, mock_urlopen):
        mock_urlopen.side_effect = Exception("Connection refused")
        ready = is_cdp_ready(9222)
        self.assertFalse(ready)

    @patch("urllib.request.urlopen")
    def test_get_cdp_tabs(self, mock_urlopen):
        mock_resp = MagicMock()
        tabs_data = [
            {"id": "tab-1", "title": "Google Gemini", "url": "https://gemini.google.com/app"},
            {"id": "tab-2", "title": "Google Sign-in", "url": "https://accounts.google.com"},
        ]
        mock_resp.read.return_value = json.dumps(tabs_data).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        mock_urlopen.return_value = mock_resp

        tabs = get_cdp_tabs(9222)
        self.assertEqual(len(tabs), 2)
        self.assertEqual(tabs[0]["title"], "Google Gemini")

    @patch("auth.is_cdp_ready")
    @patch("auth.get_cdp_tabs")
    def test_check_auth_fast_signin_detected(self, mock_tabs, mock_ready):
        mock_ready.return_value = True
        mock_tabs.return_value = [{"url": "https://accounts.google.com/ServiceLogin"}]

        res = check_auth_fast(9222)
        self.assertTrue(res["connected"])
        self.assertFalse(res["authenticated"])

    @patch("auth.is_cdp_ready")
    @patch("auth.get_cdp_tabs")
    def test_check_auth_fast_cdp_inactive(self, mock_tabs, mock_ready):
        mock_ready.return_value = False
        res = check_auth_fast(9222)
        self.assertFalse(res["connected"])
        self.assertFalse(res["authenticated"])

    @patch("subprocess.Popen")
    def test_launch_chrome_process_args(self, mock_popen):
        mock_proc = MagicMock()
        mock_popen.return_value = mock_proc

        proc = auth.launch_chrome_process(
            chrome_path="chrome.exe",
            profile_dir="temp_profile",
            port=9222,
            headless=True,
            url="https://gemini.google.com/app",
        )

        self.assertIsNotNone(proc)
        mock_popen.assert_called_once()
        called_args = mock_popen.call_args[0][0]
        self.assertIn("chrome.exe", called_args)
        self.assertIn("--remote-debugging-port=9222", called_args)
        self.assertIn("--headless=new", called_args)


if __name__ == "__main__":
    unittest.main()
