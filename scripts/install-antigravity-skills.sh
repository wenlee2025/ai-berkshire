#!/usr/bin/env bash
set -e

echo "[AI Berkshire] Syncing and installing Antigravity Skills..."
python3 scripts/sync-antigravity-skills.py

TARGET_DIR="$HOME/.gemini/config/skills"
mkdir -p "$TARGET_DIR"

cp -R .agents/skills/* "$TARGET_DIR/"

echo "[SUCCESS] Antigravity skills successfully installed to $TARGET_DIR!"
