#!/usr/bin/env bash
# Claude Code 管家 啟動腳本（macOS / Linux）
# 同時開啟管家網頁 + Claude Code CLI
# 用法：bash start.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
PORT="${AI_HUB_PORT:-8501}"

# 檢查 venv 是否存在
if [[ ! -d "$VENV_DIR" ]]; then
    echo "❌ 找不到 Python 虛擬環境。請先執行：bash install.sh"
    exit 1
fi

# 確保 ~/.claude/skills 存在
mkdir -p "$HOME/.claude/skills"

echo ""
echo "🧠 啟動 Claude Code 管家..."
echo ""

# ── 背景啟動 Streamlit（AI Hub 網頁）──
cd "$SCRIPT_DIR"
"$VENV_DIR/bin/streamlit" run app.py \
    --server.port "$PORT" \
    --server.address localhost \
    --browser.gatherUsageStats false &
STREAMLIT_PID=$!

# 等 Streamlit 啟動後確保瀏覽器已開啟
sleep 2
open "http://localhost:$PORT" 2>/dev/null || xdg-open "http://localhost:$PORT" 2>/dev/null || true

echo "✅ Claude Code 管家已在瀏覽器開啟：http://localhost:$PORT"
echo ""

# 當此腳本結束時，一起關掉 Streamlit
cleanup() {
    echo ""
    echo "🛑 正在關閉 Claude Code 管家..."
    kill "$STREAMLIT_PID" 2>/dev/null
    wait "$STREAMLIT_PID" 2>/dev/null
    echo "👋 已關閉，下次見！"
}
trap cleanup EXIT INT TERM

# ── 前景啟動 Claude Code ──
if command -v claude &>/dev/null; then
    echo "🚀 正在開啟 Claude Code..."
    echo "   （輸入 /exit 離開 Claude Code，AI Hub 也會一起關閉）"
    echo ""
    claude
else
    echo "⚠️  未偵測到 Claude Code CLI。"
    echo "   安裝方式：npm install -g @anthropic-ai/claude-code"
    echo ""
    echo "   管家網頁仍在運行中：http://localhost:$PORT"
    echo "   按 Ctrl+C 停止"
    wait "$STREAMLIT_PID"
fi
