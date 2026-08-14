# 0001. 適配 Antigravity 平台與三平台共存架構

## 狀態
Accepted (已採納)

## 背景與問題
AI Berkshire 最初設計為相容 Claude Code (`skills/*.md`) 與 OpenAI Codex (`codex-skills/`) 的投資研究框架。
隨著進入 Google Antigravity 平台，需要使整個研究框架與工具鏈深度適配 Antigravity 的自定義架構（Customization System：Rules, Skills, Plugins, MCP），同時維持對既有 Agent 平台的相容性。

## 決策
1. **Antigravity-First 全相容架構**：
   - 專案根目錄新增 `GEMINI.md` 作為 Antigravity 核心規則檔，注入嚴謹的雙源財務交叉驗證、算術手算驗算、數據截止日期基準等核心原則。
   - 建立 `.agents/skills/<name>/SKILL.md` 作為專案級 Antigravity 技能探索目錄。
   - 提供 `scripts/sync-antigravity-skills.py` 與一鍵安裝腳本 (`scripts/install-antigravity-skills.bat` / `.sh`)，支援將技能同步並安裝至全域 `~/.gemini/config/skills/`。
   - 保留與更新 `scripts/sync-codex-skills.py` 與 `scripts/sync-codex-prompts.py`，保持單一源碼 (`skills/`) 驅動多平台產出的設計。

## 後續影響
- Antigravity 用戶能即開即用，享有漸進式技能載入（Progressive Disclosure）與原生工具整合。
- 單一來源維護避免了跨平台規則漂移。
