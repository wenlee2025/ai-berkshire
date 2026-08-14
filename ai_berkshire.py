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

def _force_utf8():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

_force_utf8()


def cmd_research(args):
    """執行四大家深度個股研究。"""
    ticker = args.ticker.strip()
    print(f"\n👑 [AI Berkshire] 啟動四大家深度研究: {ticker} ...\n")
    # 調用 twstock_data / usstock_data 與 dashboard payload 生成分析
    is_tw = any(ticker.endswith(x) for x in (".TW", ".TWO")) or (ticker.isdigit() and len(ticker) == 4)
    if is_tw:
        stock_id = ticker.replace(".TW", "").replace(".TWO", "")
        subprocess.run([sys.executable, os.path.join(TOOLS_DIR, "twstock_data.py"), "quote", stock_id])
        subprocess.run([sys.executable, os.path.join(TOOLS_DIR, "twstock_data.py"), "financials", stock_id])
        subprocess.run([sys.executable, os.path.join(TOOLS_DIR, "twstock_data.py"), "revenue", stock_id])
    else:
        subprocess.run([sys.executable, os.path.join(TOOLS_DIR, "usstock_data.py"), "quote", ticker])
        subprocess.run([sys.executable, os.path.join(TOOLS_DIR, "usstock_data.py"), "financials", ticker])


def cmd_review(args):
    """執行財報精讀。"""
    ticker = args.ticker.strip()
    period = args.period or "最新"
    print(f"\n📊 [AI Berkshire] 執行財報精讀: {ticker} ({period}) ...\n")
    is_tw = any(ticker.endswith(x) for x in (".TW", ".TWO")) or (ticker.isdigit() and len(ticker) == 4)
    if is_tw:
        stock_id = ticker.replace(".TW", "").replace(".TWO", "")
        subprocess.run([sys.executable, os.path.join(TOOLS_DIR, "twstock_data.py"), "financials", stock_id])
        subprocess.run([sys.executable, os.path.join(TOOLS_DIR, "twstock_data.py"), "revenue", stock_id])
    else:
        subprocess.run([sys.executable, os.path.join(TOOLS_DIR, "usstock_data.py"), "financials", ticker])


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

    if args.command in dispatch:
        dispatch[args.command](args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
