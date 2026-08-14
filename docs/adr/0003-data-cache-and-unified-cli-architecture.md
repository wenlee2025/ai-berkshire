# ADR 0003: 本地數據快取層、統一 CLI 與全景投研 Dashboard 進化架構

## 狀態
已通過 (Accepted)

## 上下文 (Context)
在先前版本中：
1. 批量掃描美股與台股時，FinMind 免費版易因短時間頻繁請求遭遇 HTTP 402/429 速率限制，SEC EDGAR 與 Yahoo Finance 亦需要流量保護。
2. 專案各項 CLI 工具（`twstock_data.py`、`usstock_data.py`、`stock_screener.py`、`financial_rigor.py`）分散，缺乏統一進入點。
3. 投研 Dashboard 雖然支援 37 檔標的單股分析，但缺乏 Excel 拖曳上傳、同業橫向對比 (Peer Comparison) 與投資組合模擬配置 (Portfolio Simulator)。
4. 估值模組需要更貼近不同產業屬性（科技成長 vs 強週期 vs 重資產代工）的多模型矩陣支持。

## 決策 (Decision)

### 1. 建立零外部依賴的 SQLite 本地快取層 (`tools/data_cache.py`)
- 使用 Python 內建 `sqlite3` 建立 `data/berkshire.db`。
- 設定分層 TTL（Time-to-Live）：
  - 即時行情 (Quotes)：15 分鐘
  - 月營收 (Monthly Revenue)：7 天
  - 歷史財務報表 (Financial Statements)：30 天
- 支援 FinMind、Yahoo Finance、SEC EDGAR 之間的自動容錯降級。

### 2. 建立根目錄統一 CLI 工具 (`ai_berkshire.py`)
- 整合所有子系統於單一入口：
  - `python ai_berkshire.py research <symbol>`：執行四大家深度研究
  - `python ai_berkshire.py review <symbol> [period]`：執行財報精讀
  - `python ai_berkshire.py screen [--file <path>] [--market <us|tw|all>]`：執行全景選股篩
  - `python ai_berkshire.py dashboard [--port <port>]`：啟動 Web 投研儀表板
  - `python ai_berkshire.py watch`：執行月營收與論文漂移監控管線
  - `python ai_berkshire.py audit`：執行報告數據嚴謹性抽檢
  - `python ai_berkshire.py sync`：同步編譯 Antigravity 與 Codex 技能

### 3. Dashboard 全面升級三大高階功能
- **Excel/CSV 拖曳上傳**：前端直接解析並即時載入自訂清單。
- **產業同業橫向對比矩陣 (Peer Comparison)**：支援同板塊（如散熱雙雄、CCL三雄、代工巨頭）之毛利率、營益率、ROE、四大家評分多維對比。
- **投資組合配置模擬器 (Portfolio Simulator)**：支援自訂持股權重，即時試算整體組合之加權 ROE、前瞻 P/E、殖利率與護城河分級。

### 4. 多模型產業適配估值矩陣
- **成長型 (Growth)**：FCF 反向 DCF + PEG 估值
- **週期型 (Cyclical)**：P/B 河流圖 + 景氣中樞回歸
- **重資產代工型 (Asset-Heavy)**：EV/EBITDA + 自由現金流收益率 (FCF Yield)

## 後果 (Consequences)
- **優勢**：
  - 徹底免除 API 速率限制與阻擋，各工具與 Dashboard 查詢反應達到毫秒級。
  - 使用者只需記住 `python ai_berkshire.py` 單一指令即可操作整個投研系統。
  - 投研從「單股獨立分析」邁向「產業橫向對比」與「投資組合全局管理」。
- **代價**：
  - 本地需管理 `data/berkshire.db` 檔案，需提供快取清理與強制刷新機制（`--no-cache` / `--refresh`）。
