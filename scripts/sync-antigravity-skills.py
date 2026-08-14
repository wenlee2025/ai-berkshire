#!/usr/bin/env python3
"""Generate Antigravity skills (.agents/skills/*/SKILL.md) from AI Berkshire canonical skills."""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLAUDE_SKILLS = ROOT / "skills"
ANTIGRAVITY_SKILLS = ROOT / ".agents" / "skills"


def split_frontmatter(text: str) -> tuple[str | None, str]:
    if not text.startswith("---\n"):
        return None, text
    end = text.find("\n---\n", 4)
    if end == -1:
        return None, text
    return text[4:end], text[end + 5 :].lstrip("\n")


def first_heading(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return fallback


def yaml_quote(value: str) -> str:
    value = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{value}"'


def metadata_for(name: str, source_name: str, source_text: str) -> str:
    existing, body = split_frontmatter(source_text)
    if existing:
        has_name = re.search(r"(?m)^name:\s*", existing) is not None
        has_description = re.search(r"(?m)^description:\s*", existing) is not None
        lines = []
        if not has_name:
            lines.append(f"name: {name}")
        if not has_description:
            title = first_heading(body, name)
            lines.append(
                "description: "
                + yaml_quote(f"AI Berkshire skill: {title}. Source: skills/{source_name}.")
            )
        lines.append(existing.rstrip())
        return "---\n" + "\n".join(lines) + "\n---\n\n"

    title = first_heading(source_text, name)
    description = f"AI Berkshire skill: {title}. Source: skills/{source_name}."
    return (
        "---\n"
        f"name: {name}\n"
        f"description: {yaml_quote(description)}\n"
        "---\n\n"
    )


def antigravity_body(name: str, source_name: str, source_text: str) -> str:
    _, body = split_frontmatter(source_text)
    note = (
        "## Antigravity Adapter Note\n\n"
        f"This skill is generated from `skills/{source_name}` for Google Antigravity.\n\n"
        "- **Context & Baseline Date**: Confirm today's date before beginning any research. "
        "State data cutoff date in the report header. Never rely on model training cutoff.\n"
        "- **Target Equities**: Strictly focus on US Equities (USD) and Taiwan Equities (TWD).\n"
        "- **Native Tooling**:\n"
        "  - Taiwan Equities: `python tools/twstock_data.py {quote|valuation|financials|revenue|dividend} STOCK_ID`\n"
        "  - US Equities: `python tools/usstock_data.py {quote|valuation|financials|search} TICKER`\n"
        "  - Financial Rigor: `python tools/financial_rigor.py ...`\n"
        "- **Dual-source Cross Validation**: Core metrics must be verified from at least 2 independent sources. "
        "Deviations > 1% must be flagged; > 5% require consulting primary SEC/MOPS filings.\n"
        "- **Exact Market Cap**: Market cap must be verified by multiplying exact share count by current price. "
        "For ADRs (e.g., TSM vs 2330), account for depositary ratio (1 ADR = 5 common shares).\n\n"
    )
    return note + body.rstrip() + "\n"


def main() -> None:
    check = "--check" in sys.argv[1:]
    unknown_args = [arg for arg in sys.argv[1:] if arg != "--check"]
    if unknown_args:
        joined = ", ".join(unknown_args)
        raise SystemExit(f"Unknown argument(s): {joined}")

    if not check:
        ANTIGRAVITY_SKILLS.mkdir(parents=True, exist_ok=True)

    count = 0
    stale: list[str] = []
    for source in sorted(CLAUDE_SKILLS.glob("*.md")):
        name = source.stem
        source_text = source.read_text(encoding="utf-8")
        target_dir = ANTIGRAVITY_SKILLS / name
        target = target_dir / "SKILL.md"
        content = metadata_for(name, source.name, source_text) + antigravity_body(
            name, source.name, source_text
        )
        if check:
            if not target.exists() or target.read_text(encoding="utf-8") != content:
                stale.append(str(target.relative_to(ROOT)))
        else:
            target_dir.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
        count += 1

    if check:
        if stale:
            print("Antigravity skills are out of date:")
            for path in stale:
                print(f"  {path}")
            raise SystemExit(1)
        print(f"Checked {count} Antigravity skills in {ANTIGRAVITY_SKILLS.relative_to(ROOT)}")
        return

    print(f"Generated {count} Antigravity skills in {ANTIGRAVITY_SKILLS.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
