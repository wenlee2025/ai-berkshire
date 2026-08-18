# ADR 0006: 專注美股與台股雙市場架構與非核心市場清理 (Exclusive US & TW Market Focus and Non-Core Market Purge)

## 狀態
已通過 (Accepted)

## 上下文 (Context)
在專案早期原型開發階段，曾引入部分歷史 A 股研報、人民幣（CNY）計算範例與測試假數據。
隨著 AI Berkshire 全面聚焦於**美股（US Equities）**與**台股（Taiwan Equities / 37 檔全景投資清單）**，非核心市場數據與人民幣符號在單元測試或報告搜尋時造成了嚴重混淆。

## 決策 (Decision)

### 1. 市場與幣種邊界確立 (Strict Market & Currency Boundary)
- **唯一支援市場**：
  - **美股 (US Equities)**：法定幣種為 **USD ($ / 美元)**，資料來源為 SEC EDGAR (10-K/10-Q)、Yahoo Finance、Macrotrends 與 Morningstar。
  - **台股 (Taiwan Equities)**：法定幣種為 **TWD (NT$ / 新台幣)**，資料來源為 FinMind API、MOPS 公開資訊觀測站與櫃買中心。
- **嚴禁使用之幣種與市場**：
  - 全面禁止在程式碼、數據庫、算術工具與測試斷言中使用 `CNY`、`RMB`、`人民幣`、`港幣` 等非核心市場幣種。

### 2. 全量清理歷史數據與測試用例 (Full Purge)
- 徹底移除 `reports/` 目錄下過往的中國 A 股研報與漏斗報告。
- 將 `tools/financial_rigor.py` 與 `tests/test_financial_rigor.py` 之預設幣種與測試資料全面切換為 `TWD`（以華邦電 2344.TW 與台積電 2330.TW 為標準基準）。
- 在驗算告警中強化 ADR 存託比率檢查（如 1 TSM ADR = 5 股 2330 原始股）。

### 3. 技能庫與提示詞同步 (Skills & Prompts Sync)
- 更新 `skills/*.md` 提示詞中關於貨幣單位的警告說明，確保三端代理（Antigravity、Claude Code、Codex）均嚴格遵循美股/台股雙市場規範。

## 後果 (Consequences)
- **優勢**：
  - 代碼庫純度達到 100%，消除跨幣種干擾。
  - 單元測試輸出清晰易讀，全數反映真實台股與美股市值。
  - 降低代理生成研究報告時的幻覺風險。
