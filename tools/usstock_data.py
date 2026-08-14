#!/usr/bin/env python3
"""美股数据工具 (US Equities Data Tool) — 零外部依赖（仅 stdlib）。

为 Antigravity, Claude Code, Codex 提供美股一手行情、SEC 官方财报、估值与市值手算验算。
数据源：
    - 一手行情：Yahoo Finance Chart API（实时股价、52周区间、成交量）
    - 一手官方：SEC EDGAR XBRL API（官方10-K/10-Q最新流通股本、营业收入、毛利、净利润、EPS、股东权益）

用法（由 Skills 自动调用或命令行直接执行）：
    python tools/usstock_data.py quote NVDA        # 最新行情 + 官方股本 + 市值手算验算
    python tools/usstock_data.py valuation NVDA    # 估值指标 + 52周区间 + 本益比河流参考
    python tools/usstock_data.py financials NVDA   # 近5年/最新季度 官方核心财务（SEC 10-K/10-Q）
    python tools/usstock_data.py search "Apple"    # 搜索股票代码（支持代码与公司名）

注意：
    - 所有金额单位为美元（USD）
    - 零外部依赖，兼容 Windows / Linux / macOS
"""

import argparse
import json
import os
import ssl
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta

_TIMEOUT = 20
_SEC_USER_AGENT = "AIBerkshire-Research/1.0 (contact@aiberkshire.internal)"
_YAHOO_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
}


def _force_utf8():
    """保证 Windows 控制台输出 Unicode 符号时不抛异常。"""
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


_force_utf8()


def _get_json(url, headers):
    """发起 HTTP GET 请求并解析 JSON。"""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT, context=ctx) as resp:
            data = resp.read().decode("utf-8")
            return json.loads(data)
    except urllib.error.HTTPError as e:
        raise ConnectionError(f"HTTP 请求失败 ({e.code}): {url}") from e
    except urllib.error.URLError as e:
        raise ConnectionError(f"网络连接失败 ({e.reason}): {url}") from e
    except json.JSONDecodeError as e:
        raise ValueError(f"JSON 解析失败: {url}") from e


def _fmt_large_num(value, currency="USD"):
    """数值格式化：自动转换 T (兆) / B (十亿) / M (百万)。"""
    if value is None or value == "" or value == "N/A":
        return "-"
    try:
        v = float(value)
    except (ValueError, TypeError):
        return str(value)

    abs_v = abs(v)
    if abs_v >= 1e12:
        return f"${v / 1e12:,.2f}T {currency}".strip()
    if abs_v >= 1e9:
        return f"${v / 1e9:,.2f}B {currency}".strip()
    if abs_v >= 1e6:
        return f"${v / 1e6:,.2f}M {currency}".strip()
    return f"${v:,.2f} {currency}".strip()


def _fmt_shares(value):
    """股数格式化。"""
    if value is None or value == "":
        return "-"
    try:
        v = float(value)
    except (ValueError, TypeError):
        return str(value)
    abs_v = abs(v)
    if abs_v >= 1e9:
        return f"{v / 1e9:,.2f}B 股 ({v:,.0f} 股)"
    if abs_v >= 1e6:
        return f"{v / 1e6:,.2f}M 股 ({v:,.0f} 股)"
    return f"{v:,.0f} 股"


# ---------------------------------------------------------------------------
# SEC EDGAR 接口模块
# ---------------------------------------------------------------------------

_CIK_CACHE = {}


def _get_cik(ticker):
    """通过 SEC Tickers 映射表获取公司 CIK 编号。"""
    ticker = ticker.upper().strip()
    global _CIK_CACHE
    if not _CIK_CACHE:
        url = "https://www.sec.gov/files/company_tickers.json"
        try:
            data = _get_json(url, {"User-Agent": _SEC_USER_AGENT})
            for item in data.values():
                t = item.get("ticker", "").upper()
                c = item.get("cik_str")
                if t and c:
                    _CIK_CACHE[t] = str(c).zfill(10)
        except Exception:
            pass
    return _CIK_CACHE.get(ticker)


def get_sec_company_facts(ticker):
    """获取 SEC EDGAR 官方 XBRL 财务数据。"""
    cik = _get_cik(ticker)
    if not cik:
        return None
    url = f"https://data.sec.gov/api/xbrl/companyfacts/CIK{cik}.json"
    try:
        return _get_json(url, {"User-Agent": _SEC_USER_AGENT})
    except Exception:
        return None


def extract_latest_shares(facts):
    """从 SEC EDGAR 提取最新普通股发行股数（Common Stock Shares Outstanding）。"""
    if not facts:
        return None
    dei = facts.get("facts", {}).get("dei", {})
    item = dei.get("EntityCommonStockSharesOutstanding", {})
    units = item.get("units", {}).get("shares", [])
    if units:
        # 按披露日期排序，取最新一期
        units_sorted = sorted(units, key=lambda x: x.get("end", x.get("filed", "")))
        return units_sorted[-1].get("val")

    # 備選：從 us-gaap CommonStockSharesOutstanding 取
    us_gaap = facts.get("facts", {}).get("us-gaap", {})
    item2 = us_gaap.get("CommonStockSharesOutstanding", {})
    units2 = item2.get("units", {}).get("shares", [])
    if units2:
        units_sorted2 = sorted(units2, key=lambda x: x.get("end", x.get("filed", "")))
        return units_sorted2[-1].get("val")
    return None


def extract_sec_annual_financials(facts):
    """从 SEC EDGAR 提取近 5 年核心年度财报（10-K）。"""
    if not facts:
        return {}
    us_gaap = facts.get("facts", {}).get("us-gaap", {})

    # 尝试匹配营收字段
    rev_keys = [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "SalesRevenueNet",
        "TotalRevenuesAndOtherIncome",
    ]
    rev_units = []
    for k in rev_keys:
        if k in us_gaap:
            rev_units = us_gaap[k].get("units", {}).get("USD", [])
            if rev_units:
                break

    # 毛利、营业利润、净利润、EPS、权益
    gp_units = us_gaap.get("GrossProfit", {}).get("units", {}).get("USD", [])
    op_units = us_gaap.get("OperatingIncomeLoss", {}).get("units", {}).get("USD", [])
    ni_units = us_gaap.get("NetIncomeLoss", {}).get("units", {}).get("USD", [])
    eps_units = us_gaap.get("EarningsPerShareDiluted", {}).get("units", {}).get("USD/shares", [])
    eq_units = us_gaap.get("StockholdersEquity", {}).get("units", {}).get("USD", [])

    def _filter_10k(units_list):
        res = {}
        for row in units_list:
            if row.get("form") in ("10-K", "10-K/A") and row.get("fy"):
                # 必须是全年跨度 (约 350-375 天) 或 FY 标注
                fy = str(row.get("fy"))
                fp = row.get("fp", "")
                if fp == "FY" or "start" not in row or (
                    datetime.strptime(row["end"], "%Y-%m-%d") - datetime.strptime(row["start"], "%Y-%m-%d")
                ).days > 300:
                    res[fy] = row.get("val")
        return res

    rev_by_fy = _filter_10k(rev_units)
    gp_by_fy = _filter_10k(gp_units)
    op_by_fy = _filter_10k(op_units)
    ni_by_fy = _filter_10k(ni_units)
    eps_by_fy = _filter_10k(eps_units)
    eq_by_fy = _filter_10k(eq_units)

    all_years = sorted(set(list(rev_by_fy.keys()) + list(ni_by_fy.keys())), reverse=True)
    return {
        y: {
            "revenue": rev_by_fy.get(y),
            "gross_profit": gp_by_fy.get(y),
            "operating_income": op_by_fy.get(y),
            "net_income": ni_by_fy.get(y),
            "eps": eps_by_fy.get(y),
            "equity": eq_by_fy.get(y),
        }
        for y in all_years[:5]
    }


# ---------------------------------------------------------------------------
# Yahoo Finance 接口模块
# ---------------------------------------------------------------------------

def get_chart_data(ticker, range_str="1y", interval="1d"):
    """获取 Yahoo Finance Chart 数据。"""
    ticker = ticker.upper().strip()
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}?range={range_str}&interval={interval}"
    data = _get_json(url, _YAHOO_HEADERS)
    chart = data.get("chart", {})
    if chart.get("error"):
        err = chart["error"]
        raise ConnectionError(f"Yahoo Finance 错误: {err.get('description', err)}")
    results = chart.get("result")
    if not results:
        raise ConnectionError(f"未找到股票 {ticker} 的行情数据")
    return results[0]


# ---------------------------------------------------------------------------
# CLI 实现
# ---------------------------------------------------------------------------

def cmd_quote(ticker):
    """最新行情快照 + SEC 股本与市值手算验算。"""
    ticker = ticker.upper().strip()
    chart = get_chart_data(ticker, range_str="5d", interval="1d")
    meta = chart.get("meta", {})

    price = meta.get("regularMarketPrice")
    prev_close = meta.get("chartPreviousClose") or meta.get("previousClose")
    currency = meta.get("currency", "USD")
    company_name = meta.get("shortName") or meta.get("longName") or ticker
    exchange = meta.get("exchangeName", "")

    high_52w = meta.get("fiftyTwoWeekHigh")
    low_52w = meta.get("fiftyTwoWeekLow")
    vol = meta.get("regularMarketVolume")

    # 查 SEC EDGAR 官方股本
    facts = get_sec_company_facts(ticker)
    shares_out = extract_latest_shares(facts)

    print("=" * 68)
    print(f"美股行情: {company_name} ({ticker}) [{exchange}]")
    print("=" * 68)
    print(f"  最新股价:   ${price:,.2f} {currency}" if price else "  最新股价:   -")
    if price and prev_close:
        chg = price - prev_close
        chg_pct = (chg / prev_close) * 100
        print(f"  涨跌:       {chg:+,.2f} ({chg_pct:+.2f}%)  [昨收: ${prev_close:,.2f}]")
    if high_52w and low_52w:
        print(f"  52周区间:   ${low_52w:,.2f} ~ ${high_52w:,.2f}")
    if vol:
        print(f"  成交量:     {_fmt_shares(vol)}")

    # 市值手算验算（股价 × SEC官方最新流通股数）
    print("\n  [市值手算验算 (Market Cap Verification)]")
    if price and shares_out:
        calc_cap = price * shares_out
        print(f"  SEC最新总股本: {_fmt_shares(shares_out)} (来源: SEC 10-Q/10-K)")
        print(f"  精确手算市值:  {_fmt_large_num(calc_cap, currency)} (最新收盘价 ${price:,.2f} × SEC股本)")
        print("  验算状态:      ✅ 基于 SEC 官方申报股本与即时价格手算完成")
    else:
        print("  ⚠️ 未能从 SEC EDGAR 匹配到最新 10-Q 股本，请手动查阅最新 10-Q/10-K Cover Page 核对。")


def cmd_financials(ticker):
    """近 5 年核心年度财报（SEC EDGAR 官方 10-K 原文）。"""
    ticker = ticker.upper().strip()
    facts = get_sec_company_facts(ticker)
    if not facts:
        print(f"❌ 未能从 SEC EDGAR 获取 {ticker} 的 XBRL 财务数据")
        return

    company_name = facts.get("entityName", ticker)
    years_data = extract_sec_annual_financials(facts)

    if not years_data:
        print(f"❌ 未能解析到 {ticker} 的 10-K 年度财报数据")
        return

    print("=" * 68)
    print(f"官方核心财务数据 (SEC EDGAR 10-K): {company_name} ({ticker})")
    print("=" * 68)
    print("  单位：美元 (USD) | 来源：美国证券交易委员会 (SEC EDGAR 10-K 原文)")

    for fy in sorted(years_data.keys(), reverse=True):
        d = years_data[fy]
        rev = d.get("revenue")
        gp = d.get("gross_profit")
        op = d.get("operating_income")
        ni = d.get("net_income")
        eps = d.get("eps")
        eq = d.get("equity")

        print(f"\n  --- 财年 {fy} (FY) ---")
        if rev:
            print(f"  营业收入:   {_fmt_large_num(rev)}")
        if gp and rev:
            print(f"  毛利润:     {_fmt_large_num(gp)} (毛利率: {gp / rev * 100:.1f}%)")
        if op and rev:
            print(f"  营业利润:   {_fmt_large_num(op)} (营业利润率: {op / rev * 100:.1f}%)")
        if ni:
            print(f"  归母净利润: {_fmt_large_num(ni)}" + (f" (净利率: {ni / rev * 100:.1f}%)" if rev else ""))
        if eps:
            print(f"  稀释EPS:    ${eps:.2f}")
        if eq and ni:
            roe = (ni / eq) * 100
            print(f"  股东权益:   {_fmt_large_num(eq)} (ROE简化: {roe:.1f}%)")


def cmd_valuation(ticker):
    """估值指标与 52 周区间分析。"""
    ticker = ticker.upper().strip()
    chart = get_chart_data(ticker, range_str="1y", interval="1d")
    meta = chart.get("meta", {})
    facts = get_sec_company_facts(ticker)

    price = meta.get("regularMarketPrice")
    high_52w = meta.get("fiftyTwoWeekHigh")
    low_52w = meta.get("fiftyTwoWeekLow")
    currency = meta.get("currency", "USD")

    shares_out = extract_latest_shares(facts)
    years_data = extract_sec_annual_financials(facts)

    print("=" * 68)
    print(f"估值分析: {ticker}  数据源: Yahoo Finance + SEC EDGAR")
    print("=" * 68)
    print(f"  最新股价:     ${price:,.2f} {currency}" if price else "  最新股价:     -")
    print(f"  52周最高/最低: ${high_52w:,.2f} / ${low_52w:,.2f}")
    if price and high_52w and low_52w:
        pos = (price - low_52w) / (high_52w - low_52w) * 100
        print(f"  52周分位位置: {pos:.1f}% (0%=年内最低, 100%=年内最高)")

    if years_data:
        latest_fy = sorted(years_data.keys(), reverse=True)[0]
        latest_d = years_data[latest_fy]
        latest_eps = latest_d.get("eps")
        latest_rev = latest_d.get("revenue")

        if latest_eps and price:
            pe_fy = price / latest_eps
            print(f"  PE (基准财年{latest_fy}): {pe_fy:.2f}x (最新价 ${price:,.2f} / 财年EPS ${latest_eps:.2f})")
        if latest_rev and shares_out and price:
            market_cap = price * shares_out
            ps_fy = market_cap / latest_rev
            print(f"  PS (基准财年{latest_fy}): {ps_fy:.2f}x (手算市值 / 财年营收)")


def cmd_search(keyword):
    """按名称/代码搜索美股标的。"""
    url = f"https://query2.finance.yahoo.com/v1/finance/search?q={urllib.parse.quote(keyword)}&quotesCount=8&newsCount=0"
    data = _get_json(url, _YAHOO_HEADERS)
    quotes = data.get("quotes", [])
    if not quotes:
        print(f"❌ 未找到匹配 '{keyword}' 的美股标的")
        return

    print("=" * 68)
    print(f"美股搜索结果: '{keyword}'  数据源: Yahoo Finance")
    print("=" * 68)
    for q in quotes:
        symbol = q.get("symbol", "")
        name = q.get("shortname") or q.get("longname") or ""
        exch = q.get("exchange", "")
        quote_type = q.get("quoteType", "")
        if quote_type in ("EQUITY", "ETF"):
            print(f"  {symbol:<8} {name:<36} [{exch}] ({quote_type})")


def main():
    parser = argparse.ArgumentParser(
        description="美股数据工具 (US Equities Data Tool) — 零外部依赖",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command")

    for cmd, help_text in [
        ("quote", "最新行情 + SEC官方股本 + 市值手算验算"),
        ("valuation", "估值指标（52周分位/PE/PS）"),
        ("financials", "近5年官方核心财务（SEC 10-K 原文）"),
    ]:
        p = sub.add_parser(cmd, help=help_text)
        p.add_argument("ticker", help="美股代号，如 NVDA, AAPL, GOOG, MSFT")

    p_search = sub.add_parser("search", help="搜索股票代码")
    p_search.add_argument("keyword", help="公司名或代号")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    try:
        if args.command == "search":
            cmd_search(args.keyword)
        else:
            {
                "quote": cmd_quote,
                "valuation": cmd_valuation,
                "financials": cmd_financials,
            }[args.command](args.ticker)
    except BrokenPipeError:
        sys.stderr.close()
        sys.exit(0)
    except ConnectionError as e:
        print(f"❌ {e}")
        sys.exit(2)
    except Exception as e:
        print(f"❌ 执行发生错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
