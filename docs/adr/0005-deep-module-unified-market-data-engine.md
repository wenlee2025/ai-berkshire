# ADR 0005: 深度模組架構與統一市場數據引擎 (Deep Module & Unified Market Data Engine)

## 狀態
已通過 (Accepted)

## 上下文 (Context)
在專案演進過程中，系統陸續增加了台股數據介面 (`twstock_data.py`)、美股數據介面 (`usstock_data.py`)、選股篩選器 (`stock_screener.py`)、SQLite 本地快取 (`data_cache.py`)、TTM Squeeze 與凱利持倉引擎 (`ttm_squeeze_kelly.py`) 以及看板伺服器 (`dashboard_server.py`)。

這種演進產生了以下架構隱患：
1. **模組淺層化 (Shallow Modules & Leakage)**：調用方（如 CLI、看板伺服器、警報監控器）必須了解底層多個工具的細節，手動組織「查快取 ➔ 查 API ➔ 算 TTM Squeeze ➔ 算凱利持倉 ➔ 驗算市值」，導致大量重複代碼與樣板邏輯。
2. **型別缺乏契約 (Weak Typing)**：資料在各層之間多以無結構的 `dict` 傳遞，欄位名稱（如 `change_pct` vs `pct_chg`）存在拼寫與維護風險。
3. **路徑配置冗餘 (Import Path Friction)**：多個檔案依賴 `sys.path.insert(0, ...)` 進行跨層引用。

## 決策 (Decision)

### 1. 構建深度模組 `MarketDataEngine` (Deep Module Pattern)
依據 *John Ousterhout* 的深度模組原則（**小介面 + 大實作**），建立高槓桿介面 `MarketDataEngine`：
- **極簡外部介面 (Small Interface)**：
  - `get_quote(symbol) -> StockQuote`
  - `get_monthly_revenue(symbol) -> List[MonthlyRevenueRecord]`
  - `get_financials(symbol) -> List[Dict]`
  - `get_ttm_squeeze_and_kelly(symbol, capital) -> Dict`
  - `get_full_bundle(symbol, capital) -> FullStockAnalysis`
- **深層封裝實作 (Deep Implementation)**：
  - 自動處理 SQLite 快取命中與過期刷新（`data/berkshire.db`）；
  - 自動執行雙源交叉驗證與市值手算算術檢驗（偏差 $\le 1.0\%$）；
  - 自動計算 TTM Squeeze 4 態狀態機與半凱利持倉股數；
  - 自動提供跨市場（美股 / 台股）資料適配與容錯降級。

### 2. 定義強型別領域模型 (Strongly-Typed Dataclasses)
使用 Python 3 原生 `dataclasses` 定義標準領域模型：
- `StockQuote`：股票即時報價、手算市值、漲跌幅與貨幣
- `MonthlyRevenueRecord`：月營收數據、年月、YoY 同比
- `TTMSqueezeInfo`：布林帶與肯特納通道壓縮狀態、動量斜率與方向
- `KellySizingInfo`：單筆期望值 EV、盈虧比 b、半凱利比例與建議買進股數
- `FullStockAnalysis`：整合四大家評分、月營收、多模型估值與投資論文之全量結構

### 3. 重構調用端以達成高度局部性 (High Locality)
將 `ai_berkshire.py`、`pipeline_watcher.py`、`dashboard_server.py` 等調用端全數收斂至 `MarketDataEngine` 介面，調用代碼行數精簡 60% 以上。

## 後果 (Consequences)
- **優勢**：
  - **極大化調用槓桿 (Leverage)**：調用方只需一行代碼即可獲得經過雙源驗算、量化動量與資金管理加持的完整投研數據。
  - **極致局部性 (Locality)**：所有數據獲取、快取過期邏輯與算術驗算集中在單一模組內，修改一次即可全局生效。
  - **高測試純度 (Testability)**：可透過介面輕鬆對整個數據管線進行單元測試與 Mock 測試。
