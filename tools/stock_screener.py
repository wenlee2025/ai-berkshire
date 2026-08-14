#!/usr/bin/env python3
"""stock_screener.py — 动量发现 + 价值验证 选股筛（美股 & 台股）。

用法：
  python tools/stock_screener.py                   # 扫描全部预设 Watchlist
  python tools/stock_screener.py --market us       # 仅扫描美股核心池
  python tools/stock_screener.py --market tw       # 仅扫描台股核心池
  python tools/stock_screener.py 股票清單.xlsx      # 直接解析并扫描 Excel 股票清单
  python tools/stock_screener.py 2327.TW NVDA      # 扫描指定标的
  python tools/stock_screener.py --update 2327     # 交互式补充基本面数据
"""

import argparse
import csv
import json
import os
import ssl
import subprocess
import sys
import unicodedata
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timedelta

def _force_utf8():
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

_force_utf8()

# ============================================================
# 中文字符对齐助手
# ============================================================

def _display_width(s):
    w = 0
    for ch in str(s):
        if unicodedata.east_asian_width(ch) in ('F', 'W'):
            w += 2
        else:
            w += 1
    return w

def _pad_string(s, width, align='left'):
    dw = _display_width(s)
    pad = max(0, width - dw)
    if align == 'right':
        return ' ' * pad + str(s)
    elif align == 'center':
        left = pad // 2
        right = pad - left
        return ' ' * left + str(s) + ' ' * right
    else:
        return str(s) + ' ' * pad

# ============================================================
# 配置与 Watchlist
# ============================================================

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
FUND_FILE = os.path.join(DATA_DIR, "fundamentals.json")
WATCHLIST_FILE = os.path.join(DATA_DIR, "watchlist.json")

DEFAULT_WATCHLIST = {
    "us_ai_chip": ["NVDA", "AMD", "MU", "AVGO", "MRVL", "TSM"],
    "us_mega_app": ["GOOG", "META", "MSFT", "AMZN", "AAPL", "CRM", "PLTR"],
    "us_ai_infra": ["ETN", "PWR", "VRT", "CRWV", "CEG"],
    "us_fintech": ["COIN", "HOOD", "MSTR", "XYZ"],
    "tw_semiconductor": ["2330.TW", "2454.TW", "2379.TW", "3034.TW", "3661.TW", "6415.TW"],
    "tw_ai_hardware": ["2317.TW", "2382.TW", "2327.TW", "3231.TW", "6669.TW", "2308.TW", "2059.TW"],
    "tw_dividend_leaders": ["2412.TW", "2881.TW", "2882.TW", "2886.TW", "3008.TW"],
}

STOCK_NAMES = {
    # 台股常见标的
    "2330.TW": "台積電", "2330": "台積電",
    "2454.TW": "聯發科", "2454": "聯發科",
    "2379.TW": "瑞昱", "2379": "瑞昱",
    "3034.TW": "聯詠", "3034": "聯詠",
    "3661.TW": "世芯-KY", "3661": "世芯-KY",
    "6415.TW": "矽力*-KY", "6415": "矽力*-KY",
    "2317.TW": "鴻海", "2317": "鴻海",
    "2382.TW": "廣達", "2382": "廣達",
    "2327.TW": "國巨", "2327": "國巨",
    "3231.TW": "緯創", "3231": "緯創",
    "6669.TW": "緯穎", "6669": "緯穎",
    "2308.TW": "台達電", "2308": "台達電",
    "2059.TW": "川湖", "2059": "川湖",
    "2412.TW": "中華電", "2412": "中華電",
    "2881.TW": "富邦金", "2881": "富邦金",
    "2882.TW": "國泰金", "2882": "國泰金",
    "2886.TW": "兆豐金", "2886": "兆豐金",
    "3008.TW": "大立光", "3008": "大立光",
    # 美股常见标的
    "NVDA": "輝達", "AMD": "超微", "MU": "美光", "AVGO": "博通",
    "MRVL": "邁威爾", "TSM": "台積電ADR", "GOOG": "谷歌", "META": "Meta",
    "MSFT": "微軟", "AMZN": "亞馬遜", "AAPL": "蘋果", "CRM": "賽富時",
    "PLTR": "帕蘭提爾", "ETN": "伊頓", "PWR": "廣達服務", "VRT": "維諦",
    "CRWV": "CoreWeave", "CEG": "星座能源", "COIN": "Coinbase",
    "HOOD": "羅賓漢", "MSTR": "微策略", "XYZ": "Block", "SQ": "Block",
}

def register_stock_name(ticker, name):
    if not ticker or not name:
        return
    ticker = str(ticker).strip()
    name = str(name).strip()
    STOCK_NAMES[ticker] = name
    base_sym = ticker.replace(".TW", "").replace(".TWO", "")
    STOCK_NAMES[base_sym] = name

def get_display_ticker(ticker):
    """生成带中文名称的标的标识，如 2330.TW(台積電) 或 NVDA(輝達)。"""
    base_sym = ticker.replace(".TW", "").replace(".TWO", "")
    name = STOCK_NAMES.get(ticker) or STOCK_NAMES.get(base_sym)
    if name:
        return f"{ticker}({name})"
    return ticker


# ============================================================
# 文件解析器 (Excel .xlsx / CSV) — 零第三方库依赖
# ============================================================

def parse_excel_file(file_path):
    """纯标准库解析 .xlsx 文件中的股票代码与名称。"""
    tickers = []
    if not os.path.exists(file_path):
        return tickers

    try:
        with zipfile.ZipFile(file_path, "r") as z:
            shared_strings = []
            if "xl/sharedStrings.xml" in z.namelist():
                tree = ET.fromstring(z.read("xl/sharedStrings.xml"))
                for si in tree.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si"):
                    t = si.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t")
                    if t is not None and t.text:
                        shared_strings.append(t.text)
                    else:
                        r_texts = [
                            r.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t").text
                            for r in si.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}r")
                            if r.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t") is not None
                            and r.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t").text
                        ]
                        shared_strings.append("".join(r_texts))

            sheet_tree = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
            for row in sheet_tree.findall(".//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row"):
                cells = []
                for c in row.findall("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c"):
                    t = c.attrib.get("t")
                    v = c.find("{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v")
                    val = v.text if v is not None else ""
                    if t == "s" and val != "":
                        val = shared_strings[int(val)]
                    cells.append(val)
                if len(cells) >= 1:
                    raw_code = str(cells[0]).strip()
                    if raw_code and raw_code not in ("股票代碼", "代码", "Code", "Ticker", "股票代码"):
                        # 如果有第二栏名称，注册中文名
                        if len(cells) >= 2 and cells[1]:
                            raw_name = str(cells[1]).strip()
                            register_stock_name(raw_code, raw_name)
                        tickers.append(raw_code)
    except Exception as e:
        print(f"⚠️ 解析 Excel 文件失败: {e}")
    return tickers


def parse_csv_file(file_path):
    """解析 CSV 文件。"""
    tickers = []
    try:
        with open(file_path, encoding="utf-8", errors="replace") as f:
            reader = csv.reader(f)
            for row in reader:
                if row:
                    raw_code = row[0].strip()
                    if raw_code and raw_code not in ("股票代碼", "代码", "Code", "Ticker"):
                        if len(row) >= 2 and row[1]:
                            register_stock_name(raw_code, row[1].strip())
                        tickers.append(raw_code)
    except Exception as e:
        print(f"⚠️ 解析 CSV 文件失败: {e}")
    return tickers


def resolve_ticker(symbol):
    """将股票代号标准化（例如 2330 自动尝试 2330.TW 或 2330.TWO）。"""
    s = str(symbol).strip().upper()
    if s.endswith(".TW") or s.endswith(".TWO"):
        return s
    # 纯4位数字台股代码
    if s.isdigit() and len(s) == 4:
        return f"{s}.TW"
    return s


# ============================================================
# 价格数据获取 (支持 TWSE / TPEx 自动容错)
# ============================================================

def _fetch_yahoo_series(ticker, days=120):
    end_ts = int(datetime.now().timestamp())
    start_ts = int((datetime.now() - timedelta(days=days)).timestamp())
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
        f"?period1={start_ts}&period2={end_ts}&interval=1d"
    )
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=12, context=ctx) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            chart = data.get("chart", {}).get("result", [{}])[0]
            timestamps = chart.get("timestamp", [])
            quote = chart.get("indicators", {}).get("quote", [{}])[0]
            rows = []
            for i, ts in enumerate(timestamps):
                c = quote.get("close", [None] * len(timestamps))[i]
                v = quote.get("volume", [None] * len(timestamps))[i]
                h = quote.get("high", [None] * len(timestamps))[i]
                if c is not None and v is not None and h is not None:
                    dt = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
                    rows.append({"date": dt, "close": c, "high": h, "volume": v})
            if len(rows) > 15:
                return rows
    except Exception:
        pass

    try:
        result = subprocess.run(
            ["curl", "-s", "-H", "User-Agent: Mozilla/5.0", url],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            data = json.loads(result.stdout)
            chart = data.get("chart", {}).get("result", [{}])[0]
            timestamps = chart.get("timestamp", [])
            quote = chart.get("indicators", {}).get("quote", [{}])[0]
            rows = []
            for i, ts in enumerate(timestamps):
                c = quote.get("close", [None] * len(timestamps))[i]
                v = quote.get("volume", [None] * len(timestamps))[i]
                h = quote.get("high", [None] * len(timestamps))[i]
                if c is not None and v is not None and h is not None:
                    dt = datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
                    rows.append({"date": dt, "close": c, "high": h, "volume": v})
            if len(rows) > 15:
                return rows
    except Exception:
        pass

    return None


def fetch_prices(ticker, days=120):
    """获取日线历史价格，台股自动支持 TWSE (.TW) 与 TPEx (.TWO) 容错。"""
    res = _fetch_yahoo_series(ticker, days)
    if res:
        return res

    # 若为台股代号但没取到，尝试上柜 .TWO 或上市 .TW 互相切换
    if ticker.endswith(".TW"):
        alt_ticker = ticker.replace(".TW", ".TWO")
        res2 = _fetch_yahoo_series(alt_ticker, days)
        if res2:
            return res2
    elif ticker.endswith(".TWO"):
        alt_ticker = ticker.replace(".TWO", ".TW")
        res2 = _fetch_yahoo_series(alt_ticker, days)
        if res2:
            return res2
    elif ticker.isdigit() and len(ticker) == 4:
        res_tw = _fetch_yahoo_series(f"{ticker}.TW", days)
        if res_tw:
            return res_tw
        res_two = _fetch_yahoo_series(f"{ticker}.TWO", days)
        if res_two:
            return res_two

    return None


# ============================================================
# 基本面数据管理
# ============================================================

def load_fundamentals():
    if os.path.exists(FUND_FILE):
        try:
            with open(FUND_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_fundamentals(data):
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(FUND_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def update_fundamental_interactive(ticker):
    funds = load_fundamentals()
    base_sym = ticker.replace(".TW", "").replace(".TWO", "")
    t_key = ticker if ticker in funds else base_sym
    if t_key not in funds:
        funds[t_key] = {"quarters": {}}

    disp_name = get_display_ticker(ticker)
    print(f"\n  更新 {disp_name} 基本面数据")
    print(f"  已有季度：{', '.join(funds[t_key]['quarters'].keys()) or '无'}")
    q_date = input("  财报发布日 (YYYY-MM-DD): ").strip()
    label = input("  标签 (如 2026Q2): ").strip()
    rev_yoy = float(input("  营收同比增速 (%): "))
    gm = float(input("  毛利率 (%): "))
    eps_beat = float(input("  EPS超预期 (%): "))

    funds[t_key]["quarters"][q_date] = {
        "label": label, "rev_yoy": rev_yoy, "gm": gm, "eps_beat": eps_beat
    }
    save_fundamentals(funds)
    print(f"  ✅ 已保存 {disp_name} {label}")


# ============================================================
# 第一层：动量分析
# ============================================================

def check_momentum(prices):
    if not prices or len(prices) < 15:
        return None

    latest = prices[-1]
    close = latest["close"]
    lookback = min(60, len(prices) - 1)

    past_highs = [p["high"] for p in prices[-lookback-1:-1]]
    max_60d = max(past_highs) if past_highs else close

    is_60d_high = close >= max_60d
    diff_from_high_pct = (close - max_60d) / max_60d * 100 if max_60d else 0

    vol_5_len = min(5, len(prices))
    vol_20_len = min(20, len(prices))
    vol_5 = sum(p["volume"] for p in prices[-vol_5_len:]) / vol_5_len
    vol_20 = sum(p["volume"] for p in prices[-vol_20_len:]) / vol_20_len
    vol_ratio = vol_5 / vol_20 if vol_20 > 0 else 0

    close_30d = prices[-min(30, len(prices))]["close"]
    pct_30d = (close - close_30d) / close_30d * 100 if close_30d else 0

    if is_60d_high and vol_ratio > 1.2:
        status = "BREAKOUT"
        status_desc = "🔥 60日新高突破+放量"
    elif is_60d_high:
        status = "BREAKOUT_NO_VOL"
        status_desc = "⚡ 60日新高突破(量平)"
    elif diff_from_high_pct > -3.0 and pct_30d > 5.0:
        status = "NEAR_HIGH"
        status_desc = "⚡ 距新高<3% (蓄势)"
    elif pct_30d > 10.0:
        status = "STRONG"
        status_desc = "📈 30日走强 (+{:.1f}%)".format(pct_30d)
    elif pct_30d < -10.0:
        status = "WEAK"
        status_desc = "📉 短期回档 ({:.1f}%)".format(pct_30d)
    else:
        status = "CONSOLIDATE"
        status_desc = "⚪ 震荡盘整"

    triggered = (status in ("BREAKOUT", "BREAKOUT_NO_VOL")) or (status == "NEAR_HIGH" and vol_ratio > 1.3)

    return {
        "triggered": triggered,
        "status": status,
        "status_desc": status_desc,
        "close": round(close, 2),
        "date": latest["date"],
        "is_60d_high": is_60d_high,
        "diff_from_high_pct": round(diff_from_high_pct, 1),
        "vol_ratio": round(vol_ratio, 2),
        "pct_30d": round(pct_30d, 1),
    }


# ============================================================
# 第二层：价值验证
# ============================================================

def check_value(ticker, signal_date=None):
    funds = load_fundamentals()
    base_ticker = ticker.replace(".TW", "").replace(".TWO", "")
    t_key = ticker if ticker in funds else (base_ticker if base_ticker in funds else None)

    if not t_key or not funds[t_key].get("quarters"):
        return None

    quarters = funds[t_key]["quarters"]
    sorted_q = sorted(quarters.items(), key=lambda x: x[0])
    valid = [(d, q) for d, q in sorted_q if d <= signal_date] if signal_date else sorted_q

    if not valid:
        return None

    latest = valid[-1]
    prev = valid[-2] if len(valid) >= 2 else None
    prev2 = valid[-3] if len(valid) >= 3 else None

    d = latest[1]
    pd = prev[1] if prev else None
    pd2 = prev2[1] if prev2 else None

    checks = {
        "营收加速": (d["rev_yoy"] > pd["rev_yoy"]) if pd else (d["rev_yoy"] > 15),
        "毛利率扩张": (d["gm"] > pd["gm"] or d["gm"] > 50) if pd else (d["gm"] > 40),
        "盈利惊喜": d["eps_beat"] > 10,
        "营收高增长": d["rev_yoy"] > 15,
        "毛利率健康": d["gm"] > 35,
        "毛利连续改善": (d["gm"] > pd["gm"] > pd2["gm"]) if (pd and pd2) else False,
    }

    score = sum(1 for v in checks.values() if v)
    independent_pass = False
    independent_reason = ""

    if checks.get("毛利连续改善") and d["gm"] > 40:
        independent_pass = True
        independent_reason = "毛利率连续改善且>40%"
    elif d["eps_beat"] > 25:
        independent_pass = True
        independent_reason = "EPS超预期>25% (盈利反转)"

    return {
        "score": score,
        "max": 6,
        "checks": checks,
        "fund": d,
        "fund_date": latest[0],
        "fund_label": d.get("label", ""),
        "independent_pass": independent_pass,
        "independent_reason": independent_reason,
    }


def grade_signal(momentum, value):
    if not momentum:
        return "ERROR", "数据不足", ""

    status = momentum["status"]

    if momentum["triggered"]:
        if not value:
            return "WATCH", "🔥 动量突破触发！需补充基本面验证", "建议补充基本面"
        score = value["score"]
        ind = value["independent_pass"]
        if score >= 5 or (score >= 4 and ind):
            return "BUY_8%", f"确信买入 ({score}/6)", "建议 8% 确信仓位"
        elif score >= 4 or (score >= 3 and ind):
            return "BUY_5%", f"标准买入 ({score}/6)", "建议 5% 标准仓位"
        elif score >= 3:
            return "BUY_3%", f"试探买入 ({score}/6)", "建议 3% 试探仓位"
        elif ind:
            return "BUY_3%", f"独立条件通过: {value['independent_reason']}", "建议 3% 仓位"
        else:
            return "PASS", f"动量突破但基本面评分不足 ({score}/6)", "继续跟踪"

    if status == "NEAR_HIGH":
        return "ALERT", "⚡ 蓄势中 (距新高<3%)", "密切关注突破"

    if status == "STRONG":
        return "TRACK", "📈 趋势向上 (30日+{:.1f}%)".format(momentum["pct_30d"]), "顺势跟踪"

    return "HOLD", "⚪ 常态整理", "耐性等待"


def scan_ticker(ticker):
    resolved = resolve_ticker(ticker)
    prices = fetch_prices(resolved)
    if not prices:
        return None

    momentum = check_momentum(prices)
    value = check_value(resolved)
    grade, reason, advice = grade_signal(momentum, value)

    return {
        "ticker": resolved,
        "grade": grade,
        "reason": reason,
        "advice": advice,
        "momentum": momentum,
        "value": value,
    }


def main():
    parser = argparse.ArgumentParser(description="AI Berkshire 动量+价值选股筛（美股 & 台股）")
    parser.add_argument("inputs", nargs="*", help="股票代号或 Excel/CSV 文件路径，如 股票清單.xlsx 或 NVDA 2327.TW")
    parser.add_argument("--market", choices=["all", "us", "tw"], default="all", help="按市场筛选：us / tw / all")
    parser.add_argument("--update", help="交互式更新指定标的基本面数据")
    args = parser.parse_args()

    if args.update:
        update_fundamental_interactive(args.update.upper().strip())
        return

    # 初始化 / 覆寫 Watchlist
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(WATCHLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(DEFAULT_WATCHLIST, f, indent=2, ensure_ascii=False)

    source_title = ""
    tickers = []

    if args.inputs:
        for inp in args.inputs:
            if inp.endswith(".xlsx"):
                source_title = f"文件: {os.path.basename(inp)}"
                tickers.extend(parse_excel_file(inp))
            elif inp.endswith(".csv"):
                source_title = f"文件: {os.path.basename(inp)}"
                tickers.extend(parse_csv_file(inp))
            else:
                tickers.append(inp)
    else:
        for group, syms in DEFAULT_WATCHLIST.items():
            if args.market == "us" and not group.startswith("us_"):
                continue
            if args.market == "tw" and not group.startswith("tw_"):
                continue
            tickers.extend(syms)
        source_title = f"预设池 [模式: {args.market.upper()}]"

    today = datetime.now().strftime("%Y-%m-%d")
    print(f"\n{'='*84}")
    print(f"  AI Berkshire 选股筛 (美股 & 台股) — {today}  [{source_title}]")
    print(f"  待扫描标的数：{len(tickers)} 个")
    print(f"{'='*84}")

    col_code = _pad_string("标的代码(名称)", 24, "left")
    col_price = _pad_string("最新价", 11, "right")
    col_30d = _pad_string("30日涨跌", 10, "right")
    col_high = _pad_string("距60日高", 10, "right")
    col_vol = _pad_string("量比", 7, "right")
    col_status = "  动量状态与评级"

    print(f"  {col_code} {col_price} {col_30d} {col_high} {col_vol}{col_status}")
    print(f"  {'-'*80}")

    buy_signals = []
    watch_signals = []
    alert_signals = []
    strong_signals = []

    for raw_ticker in tickers:
        disp_name = get_display_ticker(raw_ticker)
        res = scan_ticker(raw_ticker)
        if not res:
            c_code = _pad_string(disp_name, 24, "left")
            c_price = _pad_string("--", 11, "right")
            c_30d = _pad_string("--", 10, "right")
            c_high = _pad_string("--", 10, "right")
            c_vol = _pad_string("--", 7, "right")
            print(f"  {c_code} {c_price} {c_30d} {c_high} {c_vol}  ⚠️ 暂无价格序列数据")
            continue

        m = res["momentum"]
        g = res["grade"]
        p_str = f"${m['close']:,.2f}"
        pct_str = f"{m['pct_30d']:+.1f}%"
        diff_str = f"{m['diff_from_high_pct']:+.1f}%"
        vol_str = f"{m['vol_ratio']:.1f}x"

        # 状态标示
        if g.startswith("BUY"):
            symbol = "🎯"
            buy_signals.append(res)
        elif g == "WATCH":
            symbol = "🔥"
            watch_signals.append(res)
        elif g == "ALERT":
            symbol = "⚡"
            alert_signals.append(res)
        elif g == "TRACK":
            symbol = "📈"
            strong_signals.append(res)
        else:
            symbol = "⚪"

        c_code = _pad_string(get_display_ticker(res['ticker']), 24, "left")
        c_price = _pad_string(p_str, 11, "right")
        c_30d = _pad_string(pct_str, 10, "right")
        c_high = _pad_string(diff_str, 10, "right")
        c_vol = _pad_string(vol_str, 7, "right")
        desc = f"{symbol} {res['reason']}"

        print(f"  {c_code} {c_price} {c_30d} {c_high} {c_vol}  {desc}")

    print(f"\n{'='*84}")
    print(f"  📋 动量与选股信号汇总")
    print(f"{'='*84}")

    if buy_signals:
        print(f"\n  🎯 突破买入信号：{len(buy_signals)} 个")
        for s in sorted(buy_signals, key=lambda x: x["grade"], reverse=True):
            m = s["momentum"]
            d_name = get_display_ticker(s['ticker'])
            print(f"     [{s['grade']}] {d_name:<22} ${m['close']:<8} (30日+{m['pct_30d']}%, 量比{m['vol_ratio']}x) → {s['advice']}")
    else:
        print(f"\n  无直接买入信号（需满足 60日新高突破 + 基本面评分≥3/6）")

    if watch_signals:
        print(f"\n  🔥 动量突破标的（需补充基本面数据）：{len(watch_signals)} 个")
        for s in watch_signals:
            m = s["momentum"]
            d_name = get_display_ticker(s['ticker'])
            print(f"     {d_name:<22} 最新价 ${m['close']} (30日+{m['pct_30d']}%, 量比{m['vol_ratio']}x) — 请用 python tools/stock_screener.py --update {s['ticker']} 补充")

    if alert_signals:
        print(f"\n  ⚡ 蓄势待发标的（距 60 日高点 < 3%）：{len(alert_signals)} 个")
        for s in sorted(alert_signals, key=lambda x: x['momentum']['pct_30d'], reverse=True):
            m = s["momentum"]
            d_name = get_display_ticker(s['ticker'])
            print(f"     {d_name:<22} 最新价 ${m['close']:<10} (距高点 {m['diff_from_high_pct']}%, 30日涨幅 {m['pct_30d']:+.1f}%)")

    if strong_signals:
        print(f"\n  📈 30日强势多头标的（30日涨幅 > 10%）：{len(strong_signals)} 个")
        for s in sorted(strong_signals, key=lambda x: x['momentum']['pct_30d'], reverse=True):
            m = s["momentum"]
            d_name = get_display_ticker(s['ticker'])
            print(f"     {d_name:<22} 最新价 ${m['close']:<10} (30日涨幅 {m['pct_30d']:+.1f}%, 距高点 {m['diff_from_high_pct']}%)")

    print(f"\n  基本面数据文件：{FUND_FILE}")
    print(f"  Watchlist文件：{WATCHLIST_FILE}\n")


if __name__ == "__main__":
    main()
