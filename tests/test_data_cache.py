#!/usr/bin/env python3
"""test_data_cache.py — 測試 SQLite 本地數據快取層。"""

import os
import sys
import time
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "tools"))

import data_cache


class TestDataCache(unittest.TestCase):
    def setUp(self):
        data_cache.init_db()
        data_cache.clear_cache("TEST_TICKER")

    def tearDown(self):
        data_cache.clear_cache("TEST_TICKER")

    def test_quote_cache_set_and_get(self):
        quote_data = {"price": 100.0, "name": "測試標的"}
        data_cache.set_quote("TEST_TICKER", quote_data, ttl_seconds=5)
        cached = data_cache.get_quote("TEST_TICKER")
        self.assertIsNotNone(cached)
        self.assertEqual(cached["price"], 100.0)
        self.assertEqual(cached["name"], "測試標的")

    def test_quote_cache_ttl_expiration(self):
        quote_data = {"price": 200.0}
        data_cache.set_quote("TEST_TICKER", quote_data, ttl_seconds=1)
        time.sleep(1.2)
        cached = data_cache.get_quote("TEST_TICKER")
        self.assertIsNone(cached, "過期快取應該返回 None")

    def test_monthly_revenue_cache(self):
        rev_rows = [{"date": "2026-07", "revenue": 100000000, "yoy": 50.0}]
        data_cache.set_monthly_revenue("TEST_TICKER", rev_rows)
        cached = data_cache.get_monthly_revenue("TEST_TICKER")
        self.assertIsNotNone(cached)
        self.assertEqual(len(cached), 1)
        self.assertEqual(cached[0]["yoy"], 50.0)


if __name__ == "__main__":
    unittest.main()
