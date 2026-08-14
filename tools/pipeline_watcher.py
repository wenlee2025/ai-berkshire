#!/usr/bin/env python3
"""pipeline_watcher.py — 自動化月營收拐點與投資論文漂移監控管線。

功能：
  1. 掃描 Watchlist 或自訂清單之最新月營收與季報表現。
  2. 偵測營收拐點 (YoY 突破、拐點翻正、急遽下滑)。
  3. 自動觸發論文漂移檢驗並在 reports/alerts/ 生成即時監控警報簡報。

用法：
  python tools/pipeline_watcher.py
  python tools/pipeline_watcher.py --file 股票清單.xlsx
"""

import argparse
import json
import os
import sys
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(BASE_DIR, "tools"))

import data_cache
import stock_screener
import twstock_data

ALERTS_DIR = os.path.join(BASE_DIR, "reports", "alerts")


def watch_stocks(stock_list=None):
    """執行全量標的月營收與基本面拐點監控。"""
    today = datetime.now().strftime("%Y-%m-%d")
    os.makedirs(ALERTS_DIR, exist_ok=True)

    if not stock_list:
        excel_path = os.path.join(BASE_DIR, "股票清單.xlsx")
        if os.path.exists(excel_path):
            stock_list = stock_screener.parse_excel_file(excel_path)
        else:
            stock_list = ["2330", "2317", "2344", "2327", "3017", "2059", "5274", "6669"]

    print(f"\n{'='*78}")
    print(f"🚀 AI Berkshire 投資論文與月營收監控管線 — {today}")
    print(f"  監控標的數：{len(stock_list)} 檔")
    print(f"{'='*78}\n")

    breakout_alerts = []
    warning_alerts = []
    normal_tracked = []

    for raw_code in stock_list:
        code = raw_code.replace(".TW", "").replace(".TWO", "").strip()
        disp_name = stock_screener.get_display_ticker(code)

        # 優先查快取
        rev_rows = data_cache.get_monthly_revenue(code)
        if not rev_rows:
            try:
                rev_rows = twstock_data._get("TaiwanStockMonthRevenue", data_id=code, start_date=twstock_data._days_ago(30 * 14))
                if rev_rows:
                    data_cache.set_monthly_revenue(code, rev_rows)
            except Exception:
                rev_rows = []

        if not rev_rows:
            # 備用價格檢查
            p_rows = stock_screener.fetch_prices(f"{code}.TW")
            if p_rows:
                latest_p = p_rows[-1]["close"]
                p_30d = ((latest_p - p_rows[-min(30, len(p_rows))]["close"]) / p_rows[-min(30, len(p_rows))]["close"] * 100)
                if p_30d > 20:
                    breakout_alerts.append({
                        "code": code, "name": disp_name, "price": latest_p, "pct_30d": p_30d,
                        "type": "MOMENTUM_BREAKOUT", "detail": f"近 30 日漲幅達 +{p_30d:.1f}%，動量強勁爆發"
                    })
            continue

        latest_rev = rev_rows[-1]
        prev_rev = rev_rows[-2] if len(rev_rows) >= 2 else None
        yoy = latest_rev.get("revenue_year_growth_rate") or 0.0
        prev_yoy = prev_rev.get("revenue_year_growth_rate") or 0.0 if prev_rev else 0.0
        rev_date = f"{latest_rev.get('revenue_year')}-{str(latest_rev.get('revenue_month')).zfill(2)}"
        rev_amount = (latest_rev.get("revenue") or 0) / 1e8

        # 判定拐點
        if yoy >= 45.0:
            breakout_alerts.append({
                "code": code, "name": disp_name, "date": rev_date, "amount": rev_amount,
                "yoy": yoy, "prev_yoy": prev_yoy, "type": "REVENUE_SURGE",
                "detail": f"{rev_date} 單月營收 {rev_amount:.1f} 億元，年增率達 +{yoy:.1f}% (上期 {prev_yoy:+.1f}%)"
            })
        elif prev_yoy < 0 and yoy > 15.0:
            breakout_alerts.append({
                "code": code, "name": disp_name, "date": rev_date, "amount": rev_amount,
                "yoy": yoy, "prev_yoy": prev_yoy, "type": "INFLECTION_POSITIVE",
                "detail": f"{rev_date} 營收由負轉正強勁反轉：YoY 由 {prev_yoy:+.1f}% 躍升至 +{yoy:.1f}%"
            })
        elif yoy <= -15.0:
            warning_alerts.append({
                "code": code, "name": disp_name, "date": rev_date, "amount": rev_amount,
                "yoy": yoy, "prev_yoy": prev_yoy, "type": "REVENUE_DROP",
                "detail": f"{rev_date} 營收大幅衰退：YoY {yoy:.1f}% (需檢視論文是否漂移)"
            })
        else:
            normal_tracked.append({"code": code, "name": disp_name, "yoy": yoy})

    # 輸出終端看板
    print(f"🔥 【強烈營收/動量爆發警報】 (共 {len(breakout_alerts)} 檔)：")
    for a in breakout_alerts:
        print(f"   🎯 [{a['code']}] {a['name']:<16} → {a['detail']}")

    if warning_alerts:
        print(f"\n⚠️ 【營收衰退與論文漂移風險】 (共 {len(warning_alerts)} 檔)：")
        for a in warning_alerts:
            print(f"   ❌ [{a['code']}] {a['name']:<16} → {a['detail']}")

    print(f"\n📈 【常態平穩跟蹤標的】：{len(normal_tracked)} 檔")

    # 生成 Alert Markdown 檔案
    alert_file = os.path.join(ALERTS_DIR, f"pipeline-alert-{today}.md")
    with open(alert_file, "w", encoding="utf-8") as f:
        f.write(f"# AI Berkshire 投資論文與營收拐點監控警報 ({today})\n\n")
        f.write(f"> **掃描基準日**：{today}  \n")
        f.write(f"> **監控總檔數**：{len(stock_list)} 檔  \n\n")

        f.write("## 1. 營收/動量強烈爆發警報 (Surge Alerts)\n\n")
        for a in breakout_alerts:
            f.write(f"- **{a['name']} ({a['code']}.TW)**：{a['detail']}\n")

        if warning_alerts:
            f.write("\n## 2. 營收下滑與論文漂移預警 (Drift Warnings)\n\n")
            for a in warning_alerts:
                f.write(f"- ⚠️ **{a['name']} ({a['code']}.TW)**：{a['detail']}\n")

        f.write(f"\n---\n*本報告由 `tools/pipeline_watcher.py` 自動生成。*\n")

    print(f"\n📝 已生成警報簡報文件：{alert_file}\n")
    return alert_file


def main():
    parser = argparse.ArgumentParser(description="AI Berkshire 投資論文與月營收監控管線")
    parser.add_argument("--file", help="自訂股票清單路徑 (如 股票清單.xlsx)")
    args = parser.parse_args()

    stock_list = None
    if args.file:
        stock_list = stock_screener.parse_excel_file(args.file)

    watch_stocks(stock_list)


if __name__ == "__main__":
    main()
