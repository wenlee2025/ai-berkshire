#!/usr/bin/env python3
"""ai_berkshire.py — AI Berkshire 統一 CLI 投研入口 (美股 & 台股)。

用法：
  python ai_berkshire.py research 2344.TW           # 個股四大家深度投資研究
  python ai_berkshire.py review 2317.TW 2026Q2      # 財報精讀與體檢
  python ai_berkshire.py screen --file 股票清單.xlsx # 全景動態選股篩
  python ai_berkshire.py watch                      # 月營收與投資論文漂移監控
  python ai_berkshire.py dashboard --port 8080      # 啟動 Web 投研儀表板
  python ai_berkshire.py audit                      # 投研報告數據嚴謹性抽檢
  python ai_berkshire.py sync                       # 同步 Antigravity / Codex 技能包
"""

import argparse
import os
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOOLS_DIR = os.path.join(BASE_DIR, "tools")
SCRIPTS_DIR = os.path.join(BASE_DIR, "scripts")

if TOOLS_DIR not in sys.path:
    sys.path.insert(0, TOOLS_DIR)

def _force_utf8():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

_force_utf8()

import market_data_engine


def cmd_research(args):
    """執行四大家深度個股研究。"""
    ticker = args.ticker.strip()
    engine = market_data_engine.DEFAULT_ENGINE
    bundle = engine.get_full_bundle(ticker)
    
    print("\n" + "=" * 68)
    print(f"👑 AI Berkshire 四大家深度投資研究: {bundle.symbol} ({bundle.name})")
    print("=" * 68)
    print(f"  最新股價:    {bundle.price:.2f} {bundle.currency} ({bundle.change_pct:+.2f}%)")
    print(f"  發行股數:    {bundle.shares_formatted}")
    print(f"  手算市值:    {bundle.market_cap_formatted}")
    print(f"  所屬板塊:    {bundle.sector}")
    
    # 評級與評分
    synth = bundle.synthesis
    scores = synth.get("radar_scores", {})
    print(f"  綜合評級:    {synth.get('verdict_label', '觀察')}")
    print(f"  綜合評分:    {scores.get('composite', 4.0):.1f} / 5.0")
    print("-" * 68)
    print(f"  ⚡ TTM Squeeze: {bundle.ttm_squeeze.get('status_label', '常態')}")
    kelly = bundle.kelly_sizing
    if kelly:
        ev = kelly.get("ev_data", {})
        stop_p = bundle.price - ev.get("risk", bundle.price * 0.08)
        print(f"  📐 半凱利建議: 配置比例 {kelly.get('applied_allocation_pct', 20.0):.1f}%, 建議買進 {kelly.get('suggested_shares', 0):,} 股 (建議停損: ${stop_p:.1f})")
    
    # 四大師視角精要
    print("-" * 68)
    print(f"  [段永平] {synth.get('dyp', {}).get('business_essence', '')}")
    print(f"  [巴菲特] {synth.get('buffett', {}).get('moat', '')}")
    print(f"  [芒  格] {synth.get('munger', {}).get('inversion', '')}")
    print(f"  [李  錄] {synth.get('lilu', {}).get('civilization', '')}")
    
    # 論文支柱與 Kill Criteria
    thesis = synth.get("thesis", {})
    pillars = thesis.get("pillars", [])
    if pillars:
        print("\n  🎯 核心論文三支柱:")
        for p in pillars:
            print(f"    • {p}")
    
    kill_criteria = thesis.get("kill_criteria", [])
    if kill_criteria:
        print("\n  ⚠️ 證偽與賣出清單 (Kill Criteria):")
        for k in kill_criteria:
            print(f"    • {k}")
    print("=" * 68 + "\n")


def cmd_review(args):
    """執行財報精讀與月營收分析。"""
    ticker = args.ticker.strip()
    period = args.period or "最新"
    engine = market_data_engine.DEFAULT_ENGINE
    bundle = engine.get_full_bundle(ticker)
    
    print("\n" + "=" * 68)
    print(f"📊 AI Berkshire 財報精讀與營收脈搏: {bundle.symbol} ({bundle.name}) [{period}]")
    print("=" * 68)
    er = bundle.synthesis.get("earnings_review", {})
    print(f"  重點摘要:    {er.get('headline', '')}")
    print(f"  獲利體檢:    {er.get('h1_summary', '')}")
    print(f"  月營收趨勢:  {er.get('monthly_revenue_signal', '')}")
    print(f"  指引達成度:  {er.get('guidance_check', '')}")
    
    # 最近 5 個月營收列印
    if bundle.monthly_revenue:
        print("\n  近幾月營收趨勢:")
        for r in bundle.monthly_revenue[-5:]:
            yoy_str = f"YoY: {r.get('yoy'):+.1f}%" if r.get('yoy') is not None else ""
            print(f"    {r.get('date')}:  {r.get('revenue', 0):,.0f} 元  {yoy_str}")
    print("=" * 68 + "\n")


def cmd_screen(args):
    """執行選股篩選。"""
    cmd = [sys.executable, os.path.join(TOOLS_DIR, "stock_screener.py")]
    if args.file:
        cmd.append(args.file)
    if args.market:
        cmd.extend(["--market", args.market])
    subprocess.run(cmd)


def cmd_watch(args):
    """執行月營收與論文監控管線。"""
    cmd = [sys.executable, os.path.join(TOOLS_DIR, "pipeline_watcher.py")]
    if args.file:
        cmd.extend(["--file", args.file])
    subprocess.run(cmd)


def cmd_dashboard(args):
    """啟動 Web 投研儀表板服務器。"""
    port = str(args.port or 8080)
    print(f"\n🚀 正在啟動投研 Dashboard (Port: {port}) ...")
    subprocess.run([sys.executable, os.path.join(TOOLS_DIR, "dashboard_server.py"), "--port", port])


def cmd_audit(args):
    """報告數據嚴謹性稽核抽檢。"""
    cmd = [sys.executable, os.path.join(TOOLS_DIR, "report_audit.py"), "extract"]
    if args.report:
        cmd.extend(["--report", args.report])
    subprocess.run(cmd)


def cmd_sync(args):
    """同步 Antigravity 與 Codex 技能庫。"""
    print("\n🔄 [AI Berkshire] 開始同步多平台技能與 Prompt...")
    subprocess.run([sys.executable, os.path.join(SCRIPTS_DIR, "sync-antigravity-skills.py")])
    subprocess.run([sys.executable, os.path.join(SCRIPTS_DIR, "sync-codex-skills.py")])
    subprocess.run([sys.executable, os.path.join(SCRIPTS_DIR, "sync-codex-prompts.py")])
    print("✅ 全平台技能同步完成！\n")


def main():
    parser = argparse.ArgumentParser(
        prog="ai_berkshire",
        description="AI Berkshire — AI 時代的美股與台股價值投資投研系統"
    )
    subparsers = parser.add_subparsers(dest="command", help="可用子指令")

    # research
    p_research = subparsers.add_parser("research", help="個股四大家深度投資研究")
    p_research.add_argument("ticker", help="股票代碼，如 2344.TW 或 NVDA")

    # review
    p_review = subparsers.add_parser("review", help="財報精讀與體檢")
    p_review.add_argument("ticker", help="股票代碼，如 2317.TW 或 NVDA")
    p_review.add_argument("period", nargs="?", default="最新", help="財報季度 (如 2026Q2 或 最新)")

    # screen
    p_screen = subparsers.add_parser("screen", help="動量+價值選股篩")
    p_screen.add_argument("--file", help="自訂清單文件 (如 股票清單.xlsx)")
    p_screen.add_argument("--market", choices=["all", "us", "tw"], default="all", help="市場篩選")

    # watch
    p_watch = subparsers.add_parser("watch", help="月營收拐點與論文漂移監控")
    p_watch.add_argument("--file", help="自訂監控清單 (如 股票清單.xlsx)")

    # dashboard
    p_dash = subparsers.add_parser("dashboard", help="啟動 Web 投研儀表板")
    p_dash.add_argument("--port", type=int, default=8080, help="端口號 (預設: 8080)")

    # audit
    p_audit = subparsers.add_parser("audit", help="報告財務數據抽檢稽核")
    p_audit.add_argument("--report", help="指定報告路徑")

    # sync
    subparsers.add_parser("sync", help="同步多平台技能文件")

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    dispatch = {
        "research": cmd_research,
        "review": cmd_review,
        "screen": cmd_screen,
        "watch": cmd_watch,
        "dashboard": cmd_dashboard,
        "audit": cmd_audit,
        "sync": cmd_sync,
    }

    handler = dispatch.get(args.command)
    if handler:
        handler(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
