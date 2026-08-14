"""Unit tests for tools/ttm_squeeze_kelly.py."""

import unittest
import math
from tools import ttm_squeeze_kelly

class TestTTMSqueezeKelly(unittest.TestCase):
    def setUp(self):
        # 構造模擬價格序列 (30 天，先收縮後向上突破)
        self.prices = []
        for i in range(25):
            # 盤整收縮期
            p = 100.0 + math.sin(i * 0.5) * 1.5
            self.prices.append({"close": p, "high": p + 1.0, "low": p - 1.0, "date": f"2026-07-{i+1:02d}"})
        # 爆發期
        for i in range(25, 30):
            p = 105.0 + (i - 25) * 4.0
            self.prices.append({"close": p, "high": p + 2.0, "low": p - 0.5, "date": f"2026-08-{i-24:02d}"})

    def test_compute_ttm_squeeze(self):
        res = ttm_squeeze_kelly.compute_ttm_squeeze(self.prices)
        self.assertIn("status", res)
        self.assertIn("momentum", res)
        self.assertIn("atr", res)
        self.assertGreater(res["atr"], 0)

    def test_compute_expected_value(self):
        # Entry 100, Stop 90 (risk 10), Target 130 (reward 30), Winrate 60%
        # b = 30 / 10 = 3.0
        # EV = 0.6 * 30 - 0.4 * 10 = 18 - 4 = +14.0
        ev = ttm_squeeze_kelly.compute_expected_value(entry_price=100.0, stop_loss=90.0, target_price=130.0, win_rate=0.60)
        self.assertEqual(ev["payoff_ratio"], 3.0)
        self.assertEqual(ev["ev_amount"], 14.0)
        self.assertTrue(ev["is_positive_ev"])

    def test_compute_kelly_sizing(self):
        # b = 3.0, p = 0.6, q = 0.4
        # Full Kelly: (3.0 * 0.6 - 0.4) / 3.0 = (1.8 - 0.4) / 3.0 = 1.4 / 3.0 = 46.67%
        # Half Kelly = 23.33%
        # Applied (capped at 20%) = 20.0%
        res = ttm_squeeze_kelly.compute_kelly_sizing(
            account_capital=1000000.0,
            entry_price=100.0,
            stop_loss=90.0,
            target_price=130.0,
            win_rate=0.60,
            max_cap_pct=0.20
        )
        self.assertEqual(res["applied_allocation_pct"], 20.0)
        self.assertEqual(res["allocated_capital"], 200000.0)
        self.assertEqual(res["suggested_shares"], 2000)
        self.assertEqual(res["max_loss_dollar"], 20000.0)
        self.assertEqual(res["account_risk_pct"], 2.0)

if __name__ == "__main__":
    unittest.main()
