@echo off
REM 雙擊此檔案即可一鍵安裝 Claude Code 管家（Windows）
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File install.ps1
pause
