#!/usr/bin/env python3
"""ttm_squeeze_kelly.py — TTM Squeeze 波動率壓縮、數學期望值 (EV) 與半凱利持倉引擎。

功能：
  1. 計算歷史 K 線之布林帶 (20, 2.0) 與肯特納通道 (20, 1.5 ATR) 壓縮狀態 (TTM Squeeze)。
  2. 計算動量振盪器 (Linear Regression Slope) 與 Squeeze 狀態機 (Squeeze On / Fired Long / Fired Short)。
  3. 計算單筆交易數學期望值 (EV)、盈虧比 (b) 與最優半凱利持倉比例 (Half Kelly %)。
  4. 根據帳戶總資金輸出建議買進股數與最大風險敞口。

用法：
  python tools/ttm_squeeze_kelly.py --ticker 2344.TW --capital 1000000
"""

import argparse
import math
import os
import sys

def _force_utf8():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

_force_utf8()

def calculate_sma(series, period):
    if len(series) < period:
        return [sum(series) / len(series)] * len(series)
    res = []
    for i in range(len(series)):
        if i < period - 1:
            res.append(sum(series[:i+1]) / (i + 1))
        else:
            res.append(sum(series[i - period + 1:i + 1]) / period)
    return res


def calculate_ema(series, period):
    if not series:
        return []
    alpha = 2.0 / (period + 1.0)
    ema = [series[0]]
    for x in series[1:]:
        ema.append(alpha * x + (1.0 - alpha) * ema[-1])
    return ema


def calculate_std(series, period):
    sma = calculate_sma(series, period)
    res = []
    for i in range(len(series)):
        start_idx = max(0, i - period + 1)
        sub = series[start_idx:i + 1]
        mean = sma[i]
        variance = sum((x - mean) ** 2 for x in sub) / len(sub)
        res.append(math.sqrt(variance))
    return res


def calculate_atr(highs, lows, closes, period=20):
    tr = []
    for i in range(len(closes)):
        h = highs[i]
        l = lows[i]
        if i == 0:
            tr.append(h - l)
        else:
            prev_c = closes[i - 1]
            tr.append(max(h - l, abs(h - prev_c), abs(l - prev_c)))
    return calculate_ema(tr, period)


def linear_regression_slope(series, period=20):
    """計算線性回歸斜率作為動量值。"""
    res = []
    x = list(range(period))
    x_mean = sum(x) / period
    x_dev = [xi - x_mean for xi in x]
    x_var = sum(xi ** 2 for xi in x_dev)

    for i in range(len(series)):
        if i < period - 1:
            res.append(0.0)
        else:
            y = series[i - period + 1:i + 1]
            y_mean = sum(y) / period
            cov = sum(x_dev[j] * (y[j] - y_mean) for j in range(period))
            slope = cov / x_var if x_var != 0 else 0.0
            res.append(slope)
    return res


def compute_ttm_squeeze(prices_list, bb_period=20, bb_sd=2.0, kc_period=20, kc_atr=1.5):
    """計算 TTM Squeeze 指標狀態。

    prices_list: list of dicts with keys: 'close', 'high', 'low', 'date'
    """
    if not prices_list or len(prices_list) < 5:
        return {
            "status": "NORMAL",
            "status_label": "⚪ 常態震盪 (No Squeeze)",
            "squeeze_on": False,
            "squeeze_days": 0,
            "momentum": 0.0,
            "momentum_direction": "NEUTRAL",
            "entry_signal": False
        }

    closes = [p["close"] for p in prices_list]
    highs = [p.get("high", p["close"] * 1.01) for p in prices_list]
    lows = [p.get("low", p["close"] * 0.99) for p in prices_list]

    # 1. Bollinger Bands
    bb_mid = calculate_sma(closes, bb_period)
    bb_std = calculate_std(closes, bb_period)
    bb_upper = [bb_mid[i] + bb_sd * bb_std[i] for i in range(len(closes))]
    bb_lower = [bb_mid[i] - bb_sd * bb_std[i] for i in range(len(closes))]

    # 2. Keltner Channels
    kc_mid = calculate_ema(closes, kc_period)
    atr = calculate_atr(highs, lows, closes, kc_period)
    kc_upper = [kc_mid[i] + kc_atr * atr[i] for i in range(len(closes))]
    kc_lower = [kc_mid[i] - kc_atr * atr[i] for i in range(len(closes))]

    # 3. Momentum
    mom_series = []
    for i in range(len(closes)):
        # Delta = Close - average(donchian_mid, sma)
        start_idx = max(0, i - bb_period + 1)
        highest = max(highs[start_idx:i + 1])
        lowest = min(lows[start_idx:i + 1])
        donchian_mid = (highest + lowest) / 2.0
        delta = closes[i] - ((donchian_mid + bb_mid[i]) / 2.0)
        mom_series.append(delta)

    mom_slope = linear_regression_slope(mom_series, bb_period)

    # 判斷近期壓縮狀態
    squeeze_flags = []
    for i in range(len(closes)):
        # BB 包含在 KC 內部即為 Squeeze On
        is_sq = (bb_upper[i] < kc_upper[i]) and (bb_lower[i] > kc_lower[i])
        squeeze_flags.append(is_sq)

    latest_sq = squeeze_flags[-1]
    prev_sq = squeeze_flags[-2] if len(squeeze_flags) >= 2 else False
    latest_mom = mom_slope[-1]
    prev_mom = mom_slope[-2] if len(mom_slope) >= 2 else 0.0

    # 計算已連續壓縮天數
    sq_days = 0
    for sq in reversed(squeeze_flags):
        if sq:
            sq_days += 1
        else:
            break

    if latest_sq:
        status = "SQUEEZE_ON"
        status_label = f"🟡 波動率極致壓縮蓄勢中 ({sq_days} 天)"
        entry_sig = False
    elif prev_sq and not latest_sq:
        if latest_mom >= 0:
            status = "SQUEEZE_FIRED_LONG"
            status_label = "🟢 多頭動量突破釋放 (Squeeze Fired Long)"
            entry_sig = True
        else:
            status = "SQUEEZE_FIRED_SHORT"
            status_label = "🔴 空頭動量跌破釋放 (Squeeze Fired Short)"
            entry_sig = False
    elif latest_mom > 0 and latest_mom > prev_mom:
        status = "MOMENTUM_EXPANDING_UP"
        status_label = "🚀 多頭動量持續擴張"
        entry_sig = True
    else:
        status = "NORMAL"
        status_label = "⚪ 常態震盪整理"
        entry_sig = False

    mom_dir = "BULLISH_RISING" if (latest_mom >= 0 and latest_mom >= prev_mom) else (
        "BULLISH_FALLING" if (latest_mom >= 0 and latest_mom < prev_mom) else (
            "BEARISH_FALLING" if (latest_mom < 0 and latest_mom <= prev_mom) else "BEARISH_RISING"
        )
    )

    return {
        "status": status,
        "status_label": status_label,
        "squeeze_on": latest_sq,
        "squeeze_days": sq_days,
        "momentum": round(latest_mom, 2),
        "momentum_direction": mom_dir,
        "entry_signal": entry_sig,
        "bb_upper": round(bb_upper[-1], 2),
        "bb_lower": round(bb_lower[-1], 2),
        "kc_upper": round(kc_upper[-1], 2),
        "kc_lower": round(kc_lower[-1], 2),
        "atr": round(atr[-1], 2)
    }


def compute_expected_value(entry_price, stop_loss, target_price, win_rate=0.65):
    """計算單筆交易數學期望值 (EV) 與盈虧比 (b)。"""
    reward = target_price - entry_price
    risk = entry_price - stop_loss

    if risk <= 0:
        risk = entry_price * 0.05
    if reward <= 0:
        reward = entry_price * 0.15

    payoff_ratio = reward / risk
    p = win_rate
    q = 1.0 - p

    ev_per_dollar = (p * payoff_ratio) - q
    ev_amount = (p * reward) - (q * risk)

    return {
        "reward": round(reward, 2),
        "risk": round(risk, 2),
        "payoff_ratio": round(payoff_ratio, 2),
        "win_rate": round(p, 2),
        "ev_amount": round(ev_amount, 2),
        "ev_per_dollar": round(ev_per_dollar, 3),
        "is_positive_ev": ev_per_dollar > 0
    }


def compute_kelly_sizing(account_capital, entry_price, stop_loss, target_price, win_rate=0.65, max_cap_pct=0.20):
    """計算凱利公式持倉比例與建議股數。"""
    ev_data = compute_expected_value(entry_price, stop_loss, target_price, win_rate)
    b = ev_data["payoff_ratio"]
    p = ev_data["win_rate"]
    q = 1.0 - p

    # Full Kelly: f* = (b*p - q) / b
    full_kelly = (b * p - q) / b if b > 0 else 0.0
    full_kelly = max(0.0, min(1.0, full_kelly))

    # Half Kelly & Quarter Kelly
    half_kelly = full_kelly * 0.5
    quarter_kelly = full_kelly * 0.25

    # 施加單股硬上限 (預設 20%)
    applied_kelly = min(half_kelly, max_cap_pct)

    allocated_capital = account_capital * applied_kelly
    suggested_shares = int(allocated_capital / entry_price) if entry_price > 0 else 0
    max_loss_dollar = suggested_shares * ev_data["risk"]
    account_risk_pct = (max_loss_dollar / account_capital * 100) if account_capital > 0 else 0.0

    return {
        "ev_data": ev_data,
        "full_kelly_pct": round(full_kelly * 100, 1),
        "half_kelly_pct": round(half_kelly * 100, 1),
        "quarter_kelly_pct": round(quarter_kelly * 100, 1),
        "applied_allocation_pct": round(applied_kelly * 100, 1),
        "allocated_capital": round(allocated_capital, 0),
        "suggested_shares": suggested_shares,
        "max_loss_dollar": round(max_loss_dollar, 0),
        "account_risk_pct": round(account_risk_pct, 2)
    }


def main():
    parser = argparse.ArgumentParser(description="TTM Squeeze 與凱利公式量化持倉引擎")
    parser.add_argument("--entry", type=float, default=177.0, help="進場價")
    parser.add_argument("--stop", type=float, default=162.0, help="停損價")
    parser.add_argument("--target", type=float, default=220.0, help="目標價")
    parser.add_argument("--winrate", type=float, default=0.65, help="預期勝率 (0.0~1.0)")
    parser.add_argument("--capital", type=float, default=1000000.0, help="總帳戶資產")
    args = parser.parse_args()

    res = compute_kelly_sizing(args.capital, args.entry, args.stop, args.target, args.winrate)
    ev = res["ev_data"]

    print("=" * 68)
    print("⚡ TTM Squeeze 數學期望值與半凱利持倉引擎")
    print("=" * 68)
    print(f"  進場價格:      ${args.entry:,.2f}")
    print(f"  停損價格:      ${args.stop:,.2f}  (潛在風險: -${ev['risk']:,.2f})")
    print(f"  目標價格:      ${args.target:,.2f}  (潛在獲利: +${ev['reward']:,.2f})")
    print(f"  盈虧比 (b):    {ev['payoff_ratio']:.2f} : 1")
    print(f"  預估勝率:      {ev['win_rate']*100:.1f}%")
    print(f"  單筆期望值 EV:  +${ev['ev_amount']:,.2f} (每承擔 $1 風險期望回報 ${ev['ev_per_dollar']:.3f})")
    print("-" * 68)
    print(f"  全凱利比例:    {res['full_kelly_pct']}%")
    print(f"  半凱利 (推薦):  {res['half_kelly_pct']}% (實盤防禦上限: {res['applied_allocation_pct']}%)")
    print(f"  建議配置資金:  ${res['allocated_capital']:,.0f}")
    print(f"  建議買進股數:  {res['suggested_shares']:,} 股")
    print(f"  單筆最大虧損:  ${res['max_loss_dollar']:,.0f} (佔總帳戶 {res['account_risk_pct']}%)")
    print("=" * 68)


if __name__ == "__main__":
    main()
