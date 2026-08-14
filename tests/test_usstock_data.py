#!/usr/bin/env python3
"""Unit tests for US Equities Data Tool (usstock_data.py)."""

import unittest
from tools.usstock_data import _fmt_large_num, _fmt_shares, _get_cik


class TestUSStockData(unittest.TestCase):
    def test_fmt_large_num(self):
        self.assertEqual(_fmt_large_num(1.5e12), "$1.50T USD")
        self.assertEqual(_fmt_large_num(2.4e9), "$2.40B USD")
        self.assertEqual(_fmt_large_num(50e6), "$50.00M USD")
        self.assertEqual(_fmt_large_num(123.45), "$123.45 USD")
        self.assertEqual(_fmt_large_num(None), "-")

    def test_fmt_shares(self):
        self.assertIn("24.20B", _fmt_shares(2.42e10))
        self.assertIn("50.00M", _fmt_shares(50e6))
        self.assertEqual(_fmt_shares(None), "-")

    def test_get_cik(self):
        nvda_cik = _get_cik("NVDA")
        self.assertEqual(nvda_cik, "0001045810")
        aapl_cik = _get_cik("AAPL")
        self.assertEqual(aapl_cik, "0000320193")


if __name__ == "__main__":
    unittest.main()
