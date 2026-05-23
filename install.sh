#!/usr/bin/env bash
# Claude Code 管家 一鍵安裝腳本（macOS）
# 自動安裝：Homebrew → Git → Python 3 → Visual Studio Code → Streamlit → 啟動 AI Hub
# 用法：bash install.sh

set -e

# ── 顏色輸出 ──
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

info()  { echo -e "${BLUE}[INFO]${NC} $1"; }
ok()    { echo -e "${GREEN}[OK]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; }

# ── 1. 確認作業系統 ──
if [[ "$(uname)" != "Darwin" ]]; then
    error "這個腳本只支援 macOS。Windows 請改用 install.ps1"
    exit 1
fi

echo ""
echo "=========================================="
echo "  🧠 Claude Code 管家 一鍵安裝（macOS）"
echo "=========================================="
echo ""

# ── 2. 安裝 Homebrew（如果沒有） ──
info "檢查 Homebrew..."
if ! command -v brew &>/dev/null; then
    warn "未偵測到 Homebrew，開始安裝..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    # Apple Silicon Mac 要把 brew 加進 PATH
    if [[ -d /opt/homebrew/bin ]]; then
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> "$HOME/.zprofile"
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi
    ok "Homebrew 安裝完成"
else
    ok "Homebrew 已安裝（$(brew --version | head -1)）"
fi

# ── 3. 安裝 Git ──
info "檢查 Git..."
if ! command -v git &>/dev/null; then
    info "安裝 Git..."
    brew install git
    ok "Git 安裝完成"
else
    ok "Git 已安裝（$(git --version)）"
fi

# ── 4. 安裝 Python 3 ──
info "檢查 Python 3..."
if ! command -v python3 &>/dev/null; then
    info "安裝 Python 3..."
    brew install python
    ok "Python 安裝完成"
else
    PY_VER=$(python3 --version)
    ok "Python 已安裝（$PY_VER）"
fi

# ── 5. 安裝 Visual Studio Code ──
info "檢查 Visual Studio Code..."
if [[ -d "/Applications/Visual Studio Code.app" ]] || command -v code &>/dev/null; then
    ok "VS Code 已安裝"
else
    info "安裝 Visual Studio Code..."
    brew install --cask visual-studio-code
    ok "VS Code 安裝完成"
fi

# ── 6. 安裝 Node.js ──
info "檢查 Node.js..."
if ! command -v node &>/dev/null; then
    info "安裝 Node.js..."
    brew install node
    ok "Node.js 安裝完成"
else
    ok "Node.js 已安裝（$(node --version)）"
fi

# ── 7. 安裝 Claude Code CLI ──
info "檢查 Claude Code CLI..."
if ! command -v claude &>/dev/null; then
    info "安裝 Claude Code CLI..."
    npm install -g @anthropic-ai/claude-code
    ok "Claude Code CLI 安裝完成"
else
    ok "Claude Code CLI 已安裝"
fi

# ── 8. 安裝 Claude Code VS Code 擴充套件 ──
if command -v code &>/dev/null; then
    info "安裝 Claude Code VS Code 擴充套件..."
    code --install-extension anthropic.claude-code --force 2>/dev/null && \
        ok "Claude Code VS Code 擴充套件安裝完成" || \
        warn "VS Code 擴充套件安裝失敗，可稍後手動安裝"
else
    warn "VS Code 指令未加入 PATH，請手動安裝 Claude Code 擴充套件"
fi

# ── 9. 建立 Python 虛擬環境並安裝 Streamlit ──
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"

info "建立 Python 虛擬環境（$VENV_DIR）..."
if [[ ! -d "$VENV_DIR" ]]; then
    python3 -m venv "$VENV_DIR"
    ok "虛擬環境建立完成"
else
    ok "虛擬環境已存在"
fi

info "安裝 Python 套件..."
"$VENV_DIR/bin/pip" install --upgrade pip --quiet
"$VENV_DIR/bin/pip" install -r "$SCRIPT_DIR/requirements.txt" --quiet
ok "Streamlit 與相依套件安裝完成"

# ── 10. 確認 ~/.claude/skills 目錄存在 ──
mkdir -p "$HOME/.claude/skills"
ok "Skills 目錄已就緒（~/.claude/skills/）"

# ── 11. 完成，自動開啟 ──
echo ""
echo "=========================================="
ok "🎉 全部安裝完成！正在開啟 Claude Code 管家..."
echo "=========================================="
echo ""

# 自動開啟管家網頁
PORT="${AI_HUB_PORT:-8501}"
cd "$SCRIPT_DIR"
"$VENV_DIR/bin/streamlit" run app.py \
    --server.port "$PORT" \
    --server.address localhost \
    --browser.gatherUsageStats false &
STREAMLIT_PID=$!

# 等 Streamlit 啟動後確保瀏覽器已開啟
sleep 2
open "http://localhost:$PORT" 2>/dev/null || true

echo ""
echo "✅ Claude Code 管家已在瀏覽器開啟：http://localhost:$PORT"
echo ""

# 如果有 Claude Code CLI，自動啟動
if command -v claude &>/dev/null; then
    echo "🚀 正在開啟 Claude Code..."
    echo "   （輸入 /exit 離開 Claude Code，AI Hub 也會一起關閉）"
    echo ""
    cleanup() {
        kill "$STREAMLIT_PID" 2>/dev/null
        wait "$STREAMLIT_PID" 2>/dev/null
    }
    trap cleanup EXIT INT TERM
    claude
else
    echo "ℹ️  下次啟動請執行：bash $SCRIPT_DIR/start.sh"
    echo "   按 Ctrl+C 停止 AI Hub"
    wait "$STREAMLIT_PID"
fi
