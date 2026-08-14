---
name: financial-data
description: "AI Berkshire skill: 財務數據獲取與交叉驗證規範 (US & Taiwan Equities). Source: skills/financial-data.md."
---

## Codex adapter note

This skill is generated from `skills/financial-data.md` so Claude Code and Codex users share one canonical workflow.

- Treat `$ARGUMENTS` as the user's request in the current Codex thread.
- When the source mentions Claude-only surfaces such as Task, Agent, WebSearch, Bash, Read, or Write, use the closest Codex capability available in this session: subagents when available, web search when needed, shell commands for local tools, and normal file edits for workspace files.
- Use shared project tools from `tools/` in this repository. Prefer running commands from the repository root with paths like `python3 tools/financial_rigor.py ...`; if the current thread starts outside the repo, locate the actual checkout path first instead of assuming a fixed home-directory path.
- Before starting research, run the `date` command to confirm today's date; treat it as the baseline for "latest" data and state the data cutoff date in the report header. Never assume the current date from training data.
- Preserve the research quality rules from `AGENTS.md`: cross-check financial data, use exact arithmetic tools for valuation/math, and clearly label uncertainty and source gaps.

# 財務數據獲取與交叉驗證規範 (US & Taiwan Equities)

本規範適用於所有涉及企業財務數據的研究。**每個關鍵數據必須來自兩個獨立來源，誤差 > 1% 須標記，> 5% 須查閱原始一手財報。**

---

## 數據源優先級

### 美股（NVDA、AAPL、GOOG、MSFT、TSM ADR、PLTR 等）

| 優先級 | 來源 | 方式 / 指令 | 說明 |
|--------|------|-------------|------|
| 1（主工具） | **tools/usstock_data.py** | `python tools/usstock_data.py quote/financials/valuation {ticker}` | 快速行情、52周區間、SEC 官方 XBRL 財報與股本、市值手算驗算 |
| 2（主信源） | **macrotrends** | `macrotrends.net/stocks/charts/{ticker}` | 10+年歷史財務序列，直接訪問 |
| 3（副信源） | **stockanalysis** | `stockanalysis.com/stocks/{ticker}/financials` | 完整季報/年報財務指標 |
| 原始一手 | **SEC EDGAR** | `sec.gov/edgar/searchedgar/companysearch` | 官方 10-K / 10-Q 原文 PDF/XBRL |

### 台股（台積電 2330、聯發科 2454、鴻海 2317、廣達 2382、中華電 2412 等）

| 優先級 | 來源 | 方式 / 指令 | 說明 |
|--------|------|-------------|------|
| 1（主工具） | **tools/twstock_data.py** | `python tools/twstock_data.py quote/financials/revenue/dividend {stock_id}` | FinMind 官方資料，含月營收、股利、損益加總與市值手算 |
| 2（副信源） | **Goodinfo台灣股市資訊網** | `goodinfo.tw/tw/StockDetail.asp?STOCK_ID={代碼}` | 歷年完整財務比率、本益比河流圖、除權息 |
| 原始一手 | **公開資訊觀測站 (MOPS)** | `mops.twse.com.tw` | 官方財報原文、每月 10 日前營收公告、重大訊息 |

---

## 核心執行規範

### 第一步：獲取數據

對每個核心財務指標（營收、毛利率、營業利益率、歸母淨利、EPS、ROE、自由現金流等），分別從**來源 1** 和**來源 2** 取數。

### 第二步：誤差計算與標記

```
誤差率 = |來源1數值 - 來源2數值| / 來源1數值 × 100%
```

| 誤差 | 處理方式 |
|------|---------|
| ≤ 1% | ✅ 一致，取來源1數值，標註兩個來源 |
| 1% ~ 5% | ⚠️ 標記「數據存在差異」，註明兩個數值，說明可能原因（GAAP vs Non-GAAP、匯率/會計口徑） |
| > 5% | ❌ 標記「數據存在重大差異」，必須查閱 SEC EDGAR 10-K 或 MOPS 原文財報，不得直接採信 |

### 第三步：數據呈現格式

每個關鍵數據必須按以下格式標註：

```
營收：$1,304.5億 USD ✅
  - macrotrends: $1,305.0億 USD
  - stockanalysis: $1,304.0億 USD
  - 誤差: 0.08%
```

差異示例：
```
淨利潤：$728.8億 USD ⚠️ 數據存在差異
  - SEC 10-K (GAAP): $728.8億 USD
  - StockAnalysis (Non-GAAP): $780.2億 USD
  - 誤差: 7.05% — 原因：會計口徑不同（GAAP vs Non-GAAP 股權激勵/稅務調整）
```

---

## 幣別與 ADR 換算規範

1. **幣別嚴格標明**：美股標的金額一律為美元（USD），台股標的一律為新台幣（TWD）。跨市場對比必須顯式標明折算匯率（如 1 USD = 32.5 TWD）。
2. **台股月營收領先優勢**：
   - 台灣上市櫃公司每月 10 日前強制公告上月營收。
   - `python tools/twstock_data.py revenue {stock_id}` 可獲取近 13 個月營收與 YoY 變化，為追蹤產業景氣拐點之最靈敏指標。
3. **ADR 換股存託比率**：
   - 台積電等標的同時存在美股 ADR（TSM）與台股普通股（2330）。
   - **1 TSM ADR = 5 股 2330 原始股**。市值計算與折溢價分析必須納入換算，嚴禁將 ADR 股價直接乘上台股發行股數。

---

## 股價與復權規範（歷史序列）

| 口徑 | 定義 | 用途 |
|------|------|------|
| 不復權 | 實際歷史成交價，除權息時跳空 | 僅用於「當前時點」最新快照 |
| 前復權 | 以最新價格為基準回調歷史價格 | 歷史股價對比、N 年漲幅、歷史 PE Band、技術突破 |
| 後復權 | 以上市首日為基準前推 | 計算歷史總回報 / 年化複合報酬率 (CAGR) |

---

## 快速取數索引

| 標的 | 主要來源 (工具) | 次要來源 (交叉驗證) | 一手原始來源 |
|------|-----------------|---------------------|-------------|
| NVDA (英偉達) | `tools/usstock_data.py quote NVDA` | macrotrends / stockanalysis | SEC EDGAR 10-K |
| AAPL (蘋果) | `tools/usstock_data.py financials AAPL` | macrotrends / stockanalysis | SEC EDGAR 10-K |
| GOOG / MSFT | `tools/usstock_data.py quote GOOG` | macrotrends | SEC EDGAR 10-K |
| 2330 台積電 | `tools/twstock_data.py quote 2330` | goodinfo.tw / macrotrends (TSM) | MOPS 公開資訊觀測站 |
| 2454 聯發科 | `tools/twstock_data.py financials 2454` | goodinfo.tw | MOPS 公開資訊觀測站 |
| 2317 鴻海 | `tools/twstock_data.py revenue 2317` | goodinfo.tw | MOPS 公開資訊觀測站 |
