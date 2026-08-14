#!/usr/bin/env python3
"""Unit tests for Taiwan Stock Data Tool (twstock_data.py)."""

import unittest
from tools.twstock_data import _fmt_yi


class TestTWStockData(unittest.TestCase):
    def test_fmt_yi(self):
        self.assertEqual(_fmt_yi(1500000000), "15.0亿")
        self.assertEqual(_fmt_yi(500000), "50.0万")
        self.assertEqual(_fmt_yi(1234), "1,234.00")
        self.assertEqual(_fmt_yi(None), "-")
        self.assertEqual(_fmt_yi(""), "-")


if __name__ == "__main__":
    unittest.main()
