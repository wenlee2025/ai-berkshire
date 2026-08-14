#!/usr/bin/env python3
"""test_ai_berkshire.py — 測試根目錄統一 CLI 工具入口。"""

import os
import subprocess
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestAIBerkshireCLI(unittest.TestCase):
    def test_cli_help(self):
        res = subprocess.run(
            [sys.executable, os.path.join(BASE_DIR, "ai_berkshire.py"), "--help"],
            capture_output=True,
            encoding="utf-8",
            errors="replace"
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("AI Berkshire", res.stdout)
        self.assertIn("research", res.stdout)
        self.assertIn("screen", res.stdout)
        self.assertIn("watch", res.stdout)
        self.assertIn("dashboard", res.stdout)

    def test_watch_command(self):
        res = subprocess.run(
            [sys.executable, os.path.join(BASE_DIR, "ai_berkshire.py"), "watch", "--file", os.path.join(BASE_DIR, "股票清單.xlsx")],
            capture_output=True,
            encoding="utf-8",
            errors="replace"
        )
        self.assertEqual(res.returncode, 0)
        self.assertIn("監控管線", res.stdout)


if __name__ == "__main__":
    unittest.main()
