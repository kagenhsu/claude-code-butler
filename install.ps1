# Claude Code 管家 一鍵安裝腳本（Windows 10/11）
# 自動安裝：winget → Git → Python 3 → Visual Studio Code → Streamlit → 啟動 AI Hub
# 用法（在 PowerShell 中執行）：
#   powershell -ExecutionPolicy Bypass -File install.ps1

$ErrorActionPreference = "Stop"

function Write-Info  { param($Msg) Write-Host "[INFO] $Msg" -ForegroundColor Cyan }
function Write-Ok    { param($Msg) Write-Host "[OK]   $Msg" -ForegroundColor Green }
function Write-Warn  { param($Msg) Write-Host "[WARN] $Msg" -ForegroundColor Yellow }
function Write-Err   { param($Msg) Write-Host "[ERR]  $Msg" -ForegroundColor Red }

Write-Host ""
Write-Host "=========================================="
Write-Host "  🧠 Claude Code 管家 一鍵安裝（Windows）"
Write-Host "=========================================="
Write-Host ""

# ── 1. 檢查 winget ──
Write-Info "檢查 winget..."
if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
    Write-Err "未偵測到 winget。請先從 Microsoft Store 安裝『應用程式安裝程式』，或升級 Windows 到較新版本。"
    Write-Err "下載：https://aka.ms/getwinget"
    exit 1
}
Write-Ok "winget 可用"

# ── 2. 安裝 Git ──
Write-Info "檢查 Git..."
if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    Write-Info "安裝 Git..."
    winget install --id Git.Git -e --accept-source-agreements --accept-package-agreements
    Write-Ok "Git 安裝完成"
} else {
    Write-Ok "Git 已安裝"
}

# ── 3. 安裝 Python 3 ──
Write-Info "檢查 Python..."
$pythonOk = $false
foreach ($cmd in @("python", "python3", "py")) {
    if (Get-Command $cmd -ErrorAction SilentlyContinue) {
        try {
            $ver = & $cmd --version 2>&1
            if ($ver -match "Python 3\.(9|1[0-9])") {
                $pythonOk = $true
                Write-Ok "Python 已安裝（$ver）"
                break
            }
        } catch {}
    }
}
if (-not $pythonOk) {
    Write-Info "安裝 Python 3.12..."
    winget install --id Python.Python.3.12 -e --accept-source-agreements --accept-package-agreements
    Write-Ok "Python 安裝完成"
    Write-Warn "請關閉並重新開啟 PowerShell 讓 PATH 生效，然後再次執行此腳本。"
    exit 0
}

# ── 4. 安裝 Visual Studio Code ──
Write-Info "檢查 Visual Studio Code..."
if (-not (Get-Command code -ErrorAction SilentlyContinue)) {
    Write-Info "安裝 Visual Studio Code..."
    winget install --id Microsoft.VisualStudioCode -e --accept-source-agreements --accept-package-agreements
    Write-Ok "VS Code 安裝完成"
} else {
    Write-Ok "VS Code 已安裝"
}

# ── 5. 安裝 Node.js ──
Write-Info "檢查 Node.js..."
if (-not (Get-Command node -ErrorAction SilentlyContinue)) {
    Write-Info "安裝 Node.js..."
    winget install --id OpenJS.NodeJS.LTS -e --accept-source-agreements --accept-package-agreements
    Write-Ok "Node.js 安裝完成"
    Write-Warn "請關閉並重新開啟 PowerShell 讓 PATH 生效，然後再次執行此腳本。"
    exit 0
} else {
    Write-Ok "Node.js 已安裝（$(node --version)）"
}

# ── 6. 安裝 Claude Code CLI ──
Write-Info "檢查 Claude Code CLI..."
if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
    Write-Info "安裝 Claude Code CLI..."
    npm install -g @anthropic-ai/claude-code
    Write-Ok "Claude Code CLI 安裝完成"
} else {
    Write-Ok "Claude Code CLI 已安裝"
}

# ── 7. 安裝 Claude Code VS Code 擴充套件 ──
if (Get-Command code -ErrorAction SilentlyContinue) {
    Write-Info "安裝 Claude Code VS Code 擴充套件..."
    try {
        code --install-extension anthropic.claude-code --force 2>$null
        Write-Ok "Claude Code VS Code 擴充套件安裝完成"
    } catch {
        Write-Warn "VS Code 擴充套件安裝失敗，可稍後手動安裝"
    }
} else {
    Write-Warn "VS Code 指令未加入 PATH，請手動安裝 Claude Code 擴充套件"
}

# ── 8. 建立 venv 並安裝 Streamlit ──
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$VenvDir = Join-Path $ScriptDir ".venv"

Write-Info "建立 Python 虛擬環境..."
if (-not (Test-Path $VenvDir)) {
    python -m venv $VenvDir
    Write-Ok "虛擬環境建立完成"
} else {
    Write-Ok "虛擬環境已存在"
}

$PipExe = Join-Path $VenvDir "Scripts\pip.exe"
Write-Info "安裝 Streamlit..."
& $PipExe install --upgrade pip --quiet
& $PipExe install -r (Join-Path $ScriptDir "requirements.txt") --quiet
Write-Ok "Streamlit 安裝完成"

# ── 9. 確認 skills 目錄 ──
$SkillsDir = Join-Path $env:USERPROFILE ".claude\skills"
New-Item -ItemType Directory -Force -Path $SkillsDir | Out-Null
Write-Ok "Skills 目錄已就緒"

# ── 10. 完成，自動開啟 ──
Write-Host ""
Write-Host "=========================================="
Write-Ok "🎉 全部安裝完成！正在開啟 Claude Code 管家..."
Write-Host "=========================================="
Write-Host ""

# 自動開啟管家網頁
$Port = if ($env:AI_HUB_PORT) { $env:AI_HUB_PORT } else { "8501" }
$StreamlitExe = Join-Path $VenvDir "Scripts\streamlit.exe"
Start-Process -FilePath $StreamlitExe -ArgumentList "run","app.py","--server.port",$Port,"--server.address","localhost","--browser.gatherUsageStats","false" -WorkingDirectory $ScriptDir -WindowStyle Minimized

Start-Sleep -Seconds 2
Start-Process "http://localhost:$Port"

Write-Host ""
Write-Ok "✅ Claude Code 管家已在瀏覽器開啟：http://localhost:$Port"
Write-Host ""

# 如果有 Claude Code CLI，自動啟動
if (Get-Command claude -ErrorAction SilentlyContinue) {
    Write-Host "🚀 正在開啟 Claude Code..."
    Write-Host "   （輸入 /exit 離開 Claude Code）"
    Write-Host ""
    claude
} else {
    Write-Host "ℹ️  下次啟動請執行：$ScriptDir\start.bat"
    Write-Host "   關閉此視窗即可停止 AI Hub"
    Read-Host "按 Enter 結束"
}
