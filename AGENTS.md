# AI Berkshire Agent & Codex Guide

This repository contains investment research workflows, reports, and shared
validation tools. Designed to support **Antigravity**, **Claude Code**, and **OpenAI Codex**.
Focus markets: **US Equities** and **Taiwan Equities**.

## Project Layout

- `skills/*.md`: Canonical workflow source files.
- `.agents/skills/*/SKILL.md`: Antigravity project skill packages.
- `codex-skills/*/SKILL.md`: Codex skill packages generated from `skills/*.md`.
- `codex-prompts/*.md`: Generated Codex custom prompts.
- `tools/*.py`: Shared financial validation and data tools (US & TW).
- `reports/`: Research outputs. Preserve existing reports.
- `scripts/sync-antigravity-skills.py`: Regenerates Antigravity skills.
- `scripts/sync-codex-skills.py`: Regenerates Codex skills.
- `scripts/sync-codex-prompts.py`: Regenerates Codex slash prompts.

## Compatibility Rules

- Treat `skills/*.md` as the canonical workflow source.
- After changing any file in `skills/`, run:
  `python3 scripts/sync-antigravity-skills.py`
  `python3 scripts/sync-codex-skills.py`
  `python3 scripts/sync-codex-prompts.py`
- Keep `GEMINI.md` for Antigravity, `CLAUDE.md` for Claude Code, and `AGENTS.md` for Codex.

## Research Quality Rules

- Before starting any research, confirm today's date and state data cutoff in report header.
- Cross-validate core financial figures across at least two independent sources (US: SEC EDGAR, Macrotrends, StockAnalysis; TW: FinMind, Goodinfo, MOPS).
- Use exact arithmetic tools for market cap and valuation:
  `python3 tools/financial_rigor.py ...`
- For US equities, use `python3 tools/usstock_data.py quote/financials/valuation TICKER`.
- For Taiwan equities, use `python3 tools/twstock_data.py quote/financials/revenue/dividend STOCK_ID`.
- Clearly label low-confidence conclusions, incomplete data, and source gaps.
- This project is for learning and research, not investment advice.
