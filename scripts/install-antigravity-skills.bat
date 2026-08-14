@echo off
setlocal enabledelayedexpansion

echo [AI Berkshire] Syncing and installing Antigravity Skills...
python scripts/sync-antigravity-skills.py
if errorlevel 1 (
    echo [ERROR] Failed to sync Antigravity skills.
    exit /b 1
)

set "TARGET_DIR=%USERPROFILE%\.gemini\config\skills"
if not exist "%TARGET_DIR%" mkdir "%TARGET_DIR%"

xcopy /E /I /Y ".agents\skills\*" "%TARGET_DIR%\"
if errorlevel 1 (
    echo [ERROR] Failed to copy skills to %TARGET_DIR%
    exit /b 1
)

echo [SUCCESS] Antigravity skills successfully installed to %TARGET_DIR%!
