@echo off
REM Claude Code 管家 啟動腳本（Windows）
REM 同時開啟管家網頁 + Claude Code CLI

setlocal
set "SCRIPT_DIR=%~dp0"
set "VENV_DIR=%SCRIPT_DIR%.venv"
if "%AI_HUB_PORT%"=="" set "AI_HUB_PORT=8501"

if not exist "%VENV_DIR%" (
    echo [ERROR] 找不到 Python 虛擬環境。請先執行：powershell -ExecutionPolicy Bypass -File install.ps1
    pause
    exit /b 1
)

if not exist "%USERPROFILE%\.claude\skills" (
    mkdir "%USERPROFILE%\.claude\skills"
)

echo.
echo 啟動 Claude Code 管家...
echo.

REM ── 背景啟動 Streamlit（AI Hub 網頁）──
cd /d "%SCRIPT_DIR%"
start "Claude Code 管家" /min "%VENV_DIR%\Scripts\streamlit.exe" run app.py --server.port %AI_HUB_PORT% --server.address localhost --browser.gatherUsageStats false

echo ✅ Claude Code 管家已啟動（http://localhost:%AI_HUB_PORT%）
echo.

REM ── 前景啟動 Claude Code ──
where claude >nul 2>nul
if %errorlevel%==0 (
    echo 🚀 正在開啟 Claude Code...
    echo    （輸入 /exit 離開 Claude Code）
    echo.
    claude
) else (
    echo ⚠️  未偵測到 Claude Code CLI。
    echo    安裝方式：npm install -g @anthropic-ai/claude-code
    echo.
    echo    管家網頁仍在運行中：http://localhost:%AI_HUB_PORT%
    echo    按任意鍵關閉...
    pause >nul
)

endlocal
