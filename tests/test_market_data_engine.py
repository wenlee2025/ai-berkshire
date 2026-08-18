#!/usr/bin/env python3
"""test_market_data_engine.py — 統一市場數據引擎 (MarketDataEngine) 單元測試。"""

import os
import sys
import unittest

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TOOLS_DIR = os.path.join(BASE_DIR, "tools")
if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

import market_data_engine
from market_data_engine import (
    FullStockAnalysis,
    KellySizingInfo,
    MarketDataEngine,
    MonthlyRevenueRecord,
    StockQuote,
    TTMSqueezeInfo,
)


class TestMarketDataEngine(unittest.TestCase):

    def setUp(self):
        self.engine = MarketDataEngine()

    def test_normalize_symbol(self):
        """測試股票代碼標準化。"""
        self.assertEqual(self.engine.normalize_symbol("2330"), ("2330", "2330.TW"))
        self.assertEqual(self.engine.normalize_symbol("2344.TW"), ("2344", "2344.TW"))
        self.assertEqual(self.engine.normalize_symbol("6274.TWO"), ("6274", "6274.TWO"))
        self.assertEqual(self.engine.normalize_symbol("nvda"), ("NVDA", "NVDA"))
        self.assertEqual(self.engine.normalize_symbol("AAPL"), ("AAPL", "AAPL"))

    def test_get_quote_tw(self):
        """測試台股報價與手算市值。"""
        quote = self.engine.get_quote("2330.TW")
        self.assertIsInstance(quote, StockQuote)
        self.assertEqual(quote.symbol, "2330.TW")
        self.assertEqual(quote.name, "台積電")
        self.assertGreater(quote.price, 0)
        self.assertGreater(quote.market_cap_raw, 0)
        self.assertTrue(quote.market_cap_verified)

    def test_get_quote_winbond(self):
        """測試華邦電報價與屬性。"""
        quote = self.engine.get_quote("2344")
        self.assertIsInstance(quote, StockQuote)
        self.assertEqual(quote.symbol, "2344.TW")
        self.assertEqual(quote.name, "華邦電")
        self.assertEqual(quote.sector, "利基型DRAM/NOR")

    def test_get_monthly_revenue(self):
        """測試月營收數據結構與解析。"""
        revs = self.engine.get_monthly_revenue("2344.TW")
        self.assertIsInstance(revs, list)
        self.assertGreaterEqual(len(revs), 1)
        self.assertIsInstance(revs[0], MonthlyRevenueRecord)
        self.assertIsNotNone(revs[0].date)
        self.assertGreater(revs[0].revenue, 0)

    def test_get_ttm_squeeze_and_kelly(self):
        """測試 TTM Squeeze 與半凱利持倉量化。"""
        res = self.engine.get_ttm_squeeze_and_kelly("2330.TW", capital=1000000.0)
        self.assertIn("ttm_squeeze", res)
        self.assertIn("kelly_sizing", res)

        sq = res["ttm_squeeze"]
        self.assertIn("status", sq)
        self.assertIn("momentum", sq)

        kelly = res["kelly_sizing"]
        self.assertIn("suggested_shares", kelly)
        self.assertIn("applied_allocation_pct", kelly)
        self.assertLessEqual(kelly["applied_allocation_pct"], 20.0)

    def test_get_full_bundle(self):
        """測試全量投研數據包結構。"""
        bundle = self.engine.get_full_bundle("2344.TW")
        self.assertIsInstance(bundle, FullStockAnalysis)
        self.assertEqual(bundle.symbol, "2344.TW")
        self.assertIn("dyp", bundle.synthesis)
        self.assertIn("buffett", bundle.synthesis)
        self.assertIn("munger", bundle.synthesis)
        self.assertIn("lilu", bundle.synthesis)
        self.assertIn("thesis", bundle.synthesis)

        # 檢驗專屬 Kill Criteria
        kill_criteria = bundle.synthesis["thesis"]["kill_criteria"]
        self.assertTrue(any("利基型 DRAM" in k or "高雄新廠" in k for k in kill_criteria))

        # 測試 to_dict
        d = bundle.to_dict()
        self.assertIsInstance(d, dict)
        self.assertEqual(d["symbol"], "2344.TW")

    def test_scan_universe(self):
        """測試批量宇宙標的掃描。"""
        results = self.engine.scan_universe(["2330.TW", "2344.TW", "2059.TW"])
        self.assertEqual(len(results), 3)
        self.assertEqual(results[0].symbol, "2330.TW")
        self.assertEqual(results[1].symbol, "2344.TW")
        self.assertEqual(results[2].symbol, "2059.TW")


if __name__ == "__main__":
    unittest.main()
