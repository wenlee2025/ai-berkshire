#!/usr/bin/env python3
"""data_cache.py — AI Berkshire 本地 SQLite 數據快取層 (零外部依賴)。

提供行情、月營收與財務數據的 TTL 本地持久化快取，防止觸發 API 速率限制 (HTTP 402/429)，
並支援多源容錯切換。
"""

import json
import os
import sqlite3
import time
from datetime import datetime

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DB_PATH = os.path.join(DATA_DIR, "berkshire.db")


def _get_conn():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10.0)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化快取資料表。"""
    conn = _get_conn()
    with conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS quotes (
                symbol TEXT PRIMARY KEY,
                data_json TEXT NOT NULL,
                updated_at REAL NOT NULL,
                ttl REAL NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS monthly_revenues (
                symbol TEXT PRIMARY KEY,
                data_json TEXT NOT NULL,
                updated_at REAL NOT NULL,
                ttl REAL NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS financials (
                symbol TEXT PRIMARY KEY,
                data_json TEXT NOT NULL,
                updated_at REAL NOT NULL,
                ttl REAL NOT NULL
            )
        """)
    conn.close()


init_db()


def get_cached(table_name, symbol):
    """獲取快取資料，若過期或不存在則返回 None。"""
    sym = symbol.strip().upper()
    now = time.time()
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute(f"SELECT data_json, updated_at, ttl FROM {table_name} WHERE symbol = ?", (sym,))
        row = cur.fetchone()
        conn.close()
        if row:
            if now - float(row["updated_at"]) <= float(row["ttl"]):
                return json.loads(row["data_json"])
    except Exception as e:
        print(f"⚠️ Cache read error ({table_name}/{sym}): {e}")
    return None


def set_cached(table_name, symbol, data, ttl_seconds):
    """寫入或更新快取資料。"""
    sym = symbol.strip().upper()
    now = time.time()
    data_json = json.dumps(data, ensure_ascii=False)
    try:
        conn = _get_conn()
        with conn:
            conn.execute(f"""
                INSERT INTO {table_name} (symbol, data_json, updated_at, ttl)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    data_json = excluded.data_json,
                    updated_at = excluded.updated_at,
                    ttl = excluded.ttl
            """, (sym, data_json, now, float(ttl_seconds)))
        conn.close()
    except Exception as e:
        print(f"⚠️ Cache write error ({table_name}/{sym}): {e}")


def get_quote(symbol):
    return get_cached("quotes", symbol)


def set_quote(symbol, data, ttl_seconds=900):  # 預設 15 分鐘
    set_cached("quotes", symbol, data, ttl_seconds)


def get_monthly_revenue(symbol):
    return get_cached("monthly_revenues", symbol)


def set_monthly_revenue(symbol, data, ttl_seconds=86400 * 7):  # 預設 7 天
    set_cached("monthly_revenues", symbol, data, ttl_seconds)


def get_financials(symbol):
    return get_cached("financials", symbol)


def set_financials(symbol, data, ttl_seconds=86400 * 30):  # 預設 30 天
    set_cached("financials", symbol, data, ttl_seconds)


def clear_cache(symbol=None):
    """清理快取。"""
    conn = _get_conn()
    with conn:
        if symbol:
            sym = symbol.strip().upper()
            conn.execute("DELETE FROM quotes WHERE symbol = ?", (sym,))
            conn.execute("DELETE FROM monthly_revenues WHERE symbol = ?", (sym,))
            conn.execute("DELETE FROM financials WHERE symbol = ?", (sym,))
        else:
            conn.execute("DELETE FROM quotes")
            conn.execute("DELETE FROM monthly_revenues")
            conn.execute("DELETE FROM financials")
    conn.close()
