# AI Berkshire — 專案指令 (Claude Code 指引)

## 專案概述

基於價值投資四大家（巴菲特、芒格、段永平、李錄）研究框架的 AI 投資研究 Skill 合集。
專注於**美股（US Equities）**與**台股（Taiwan Equities）**的深度基本面與量化研究。
相容於 **Antigravity**、**Claude Code** 與 **OpenAI Codex**。

## 專案結構

```
skills/          — 投研 Skill 定義源碼（.md）
.agents/skills/  — Antigravity 技能探索目錄（由腳本同步）
codex-skills/    — OpenAI Codex 技能目錄（由腳本同步）
tools/           — 輔助工具（twstock_data.py, usstock_data.py, financial_rigor.py, report_audit.py）
reports/         — 投資研究報告輸出
docs/adr/        — 架構決策記錄
```

## 報告目錄結構

所有報告按**公司名**建資料夾，公司相關的所有報告放在對應資料夾內：

```
reports/
├── AI产业研究/              — AI產業鏈全景研究
├── 台積電/                  — 台積電所有研究報告
│   ├── 台積電-research-20260813.md
│   ├── 台積電-earnings-2026Q2.md
│   └── 台積電-thesis.md
├── NVDA/                    — 英偉達研究報告
├── reports/portfolio-latest.md — 投資組合總覽
└── 多公司對比-checklist-20260408.md
```

## 投研分析核心原則（最高優先級）

- **最新基準日檢驗**：研究前必須先確認真實日期，作為最新數據基準。
- **客觀事實優先**：所有投研分析必須基於事實和數據，嚴禁主觀臆斷。
- **雙源交叉驗證**：核心數據必須來自至少兩個獨立來源（美股：SEC EDGAR + Macrotrends/StockAnalysis；台股：FinMind + Goodinfo/MOPS），誤差 >1% 須標記，>5% 打回。
- **市值精確手算**：透過「股價 × 最新總股本」手算驗算，並注意台股 TWD / 美股 USD 幣別與 ADR 存託比率（1 TSM ADR = 5 股 2330）。
- **工具調用**：
  - 台股：`python3 tools/twstock_data.py quote 2330`
  - 美股：`python3 tools/usstock_data.py quote NVDA`
  - 財務嚴謹性：`python3 tools/financial_rigor.py ...`

## 多平台同步規則

- 修改 `skills/*.md` 後，務必執行：
  ```bash
  python3 scripts/sync-antigravity-skills.py
  python3 scripts/sync-codex-skills.py
  python3 scripts/sync-codex-prompts.py
  ```
