# AI Berkshire Antigravity Guide

本專案為 AI 價值投資研究框架，專注於**美股（US Equities）**與**台股（Taiwan Equities）**的深度基本面與量化研究。
本文件定義 Antigravity 代理在此專案下的核心原則、自定義規範與研究品質要求。

## 專案核心原則 (Core Principles)

1. **最新基準日檢驗 (Baseline Date Verification)**：
   - 在展開任何研究前，必須先調用時間/日期指令獲取當前真實日期。
   - 將該日期視為「最新數據」的基準點（包含最新股價、市值、最新季度/年度申報），並在研究報告標頭明確標註資料截止日期（Data Cutoff Date）。嚴禁依賴模型訓練切斷日。

2. **雙源交叉驗證 (Dual-Source Cross-Validation)**：
   - 涉及核心財務指標（營收、毛利率、營業利益、歸母淨利、EPS、ROE、自由現金流）時，必須來自至少兩個獨立資料源。
   - 誤差 ≤ 1%：視為一致，採用主信源數據並標註兩源；
   - 誤差 1% ~ 5%：標註「數據存在差異」並說明可能原因（如 GAAP vs Non-GAAP、匯率口徑）；
   - 誤差 > 5%：視為重大差異，必須調閱原始一手財報（SEC EDGAR 10-K/10-Q 或公開資訊觀測站 MOPS），不得直接採信。

3. **市值與財務算術手算驗算 (Exact Arithmetic & Verification)**：
   - 嚴禁估算或盲目採信第三方網站顯示市值。
   - 市值必須透過「最新實際股價 × 最新流通股數」精確計算，並調用 `tools/financial_rigor.py verify-market-cap` 驗算。
   - 針對台積電（2330 / TSM）等具有 ADR 標的，必須注意存託比率（1 TSM ADR = 5 股 2330 原始股），嚴禁直接以 ADR 股價乘上台股發行股數。

4. **數據工具優先原則 (Tooling-First Policy)**：
   - **台股**：優先調用 `python3 tools/twstock_data.py {quote|valuation|financials|revenue|dividend|search} {stock_id}`（FinMind API，含月營收、股利與市值驗算）。
   - **美股**：優先調用 `python3 tools/usstock_data.py {quote|valuation|financials|search} {ticker}`（支援 Yahoo/SEC/Macrotrends 數據）及 `python3 tools/morningstar_fair_value.py`。
   - **算術與估值驗證**：優先調用 `python3 tools/financial_rigor.py {verify-market-cap|verify-valuation|cross-validate|calc}`。
   - **報告稽核**：發布前必須通過 `python3 tools/report_audit.py extract --report reports/xxx.md` 抽檢。

5. **語言與領域術語規範**：
   - 輸出語言以繁體中文為主。
   - 嚴格遵守根目錄 [CONTEXT.md](file:///d:/AI%20Berkshire/CONTEXT.md) 所定義的領域模型與術語規範。
   - 本專案僅供學習與研究，不構成任何個人化投資建議。

## 專案結構與技能探索 (Customizations)

- `skills/*.md`：核心 Skill 定義源碼。
- `.agents/skills/*/SKILL.md`：Antigravity 專案級技能封裝目錄（由 `scripts/sync-antigravity-skills.py` 生成）。
- `codex-skills/*/SKILL.md`：OpenAI Codex 技能目錄。
- `tools/*.py`：共用財務驗證與數據工具。
- `reports/`：研究報告產出目錄（保留歷史報告以供回溯）。
- `scripts/`：同步與本地環境安裝腳本。

## 技能與腳本維護規則

- 修改 `skills/*.md` 後，必須執行：
  ```bash
  python3 scripts/sync-antigravity-skills.py
  python3 scripts/sync-codex-skills.py
  python3 scripts/sync-codex-prompts.py
  ```
- 驗證同步狀態：
  ```bash
  python3 scripts/sync-antigravity-skills.py --check
  ```
