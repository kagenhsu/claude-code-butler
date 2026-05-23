# 🧠 Claude Code 管家 (Claude Code Butler)

> 專為 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 打造的本機管理介面。
> 用瀏覽器輕鬆管理 Skills、雲端模型、本地模型，不用記任何指令。

![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-blue)
![License](https://img.shields.io/badge/license-MIT-green)

## 這是什麼？

**Claude Code** 是 Anthropic 官方的 AI 程式助手，在終端機裡幫你寫程式、改檔案、跑指令。

**Claude Code 管家**是它的圖形化管理介面 — 你不需要記指令，只要打開瀏覽器，就能：

- 用網頁建立、編輯、刪除 Claude Code 的 **Skill**（教 AI 做特定任務的腳本）
- 管理你的 **API Key**（Claude / OpenAI / Gemini）
- 偵測並管理電腦上的**本地模型**（Ollama / LM Studio）
- 在**對話沙盒**裡比較不同 AI 的回答
- 透過 **LINE / Telegram / Discord** 從手機也能用 AI
- 監控 **AI 自動化任務**的執行狀態

## ✨ 功能一覽

| 功能 | 狀態 | 說明 |
|------|------|------|
| 📂 技能管理 | ✅ 可用 | 視覺化新增/編輯/刪除 Claude Code Skill，含 3 個範本一鍵建立 |
| 🤖 雲端模型 | 🔜 v2 | Claude / OpenAI / Gemini API Key 管理 |
| 💻 本地模型 | 🔜 v2 | Ollama / LM Studio 偵測與管理 |
| 💬 對話沙盒 | 🔜 v2 | 並排比較不同模型的回答 |
| 📱 通訊軟體 | 🔜 v2 | LINE / Telegram / Discord Bot |
| 🤖 自動化任務 | 🔜 v2 | 監控 AI Agent 執行狀態與排程任務 |
| ⚙️ 設定 | ✅ 可用 | 系統資訊、路徑檢視 |

## 🚀 安裝方式

### 零基礎安裝（推薦）

完全不需要事先安裝任何東西，腳本會自動幫你裝好：
**Git → Python → Node.js → Claude Code CLI → VS Code → Claude Code VS Code 擴充套件**

#### macOS

在 Finder 中找到 `ai-hub` 資料夾，**雙擊 `安裝.command`** 即可。

或在終端機輸入：
```bash
bash install.sh
```

#### Windows

在檔案總管中找到 `ai-hub` 資料夾，**雙擊 `安裝.bat`** 即可。

或在 PowerShell 輸入：
```powershell
powershell -ExecutionPolicy Bypass -File install.ps1
```

安裝完成後，**瀏覽器會自動打開管家網頁，終端機會啟動 Claude Code**，不需要額外操作。

### 從 GitHub 下載安裝

```bash
git clone https://github.com/kagenhsu/claude-code-butler.git
cd claude-code-butler
bash install.sh        # macOS / Linux
```

## ▶️ 日常使用

安裝完成後，每次要用只需要：

| 平台 | 方法一：雙擊 | 方法二：指令 |
|------|-------------|-------------|
| macOS / Linux | 雙擊 `啟動.command` | `bash start.sh` |
| Windows | 雙擊 `啟動.bat` | `start.bat` |

啟動後會同時開啟：
1. **瀏覽器** — 管家網頁（`http://localhost:8501`）
2. **終端機** — Claude Code CLI，直接開始跟 AI 對話

### 第一次使用？

1. 雙擊「啟動」，瀏覽器會自動打開
2. 點左側「📂 技能管理」
3. 選一個範本，按「一鍵建立」
4. 回到終端機的 Claude Code，輸入 `/skill 名稱` 就能使用！

## 📖 什麼是 Skill？

Skill 是教 Claude Code 做特定任務的「腳本檔」。例如：

- **程式碼審查** — 讓 Claude 用固定格式幫你 review code
- **Git 提交助手** — 讓 Claude 自動生成 commit message
- **測試產生器** — 讓 Claude 幫你寫單元測試

建立 Skill 後，在 Claude Code 裡輸入 `/skill 名稱` 就會啟動。

管家提供 3 個現成範本，一鍵就能建立，不需要自己寫。

## 📦 搬到別台電腦

1. 把整個資料夾複製過去（**不要**複製 `.venv/`，目標電腦會自動重建）
2. 雙擊「安裝」
3. 完成

## 🗂️ 檔案結構

```
claude-code-butler/
├── 安裝.command / 安裝.bat     # 雙擊即可安裝（macOS / Windows）
├── 啟動.command / 啟動.bat     # 雙擊即可啟動（管家網頁 + Claude Code）
├── app.py                      # Streamlit 主入口
├── pages/                      # 各功能頁面
│   ├── 1_技能管理.py            # Skills 管理（v1 完整功能）
│   ├── 2_雲端模型.py            # 雲端模型（v2）
│   ├── 3_本地模型.py            # 本地模型（v2）
│   ├── 4_對話沙盒.py            # 對話沙盒（v2）
│   ├── 5_設定.py                # 系統資訊與設定
│   ├── 6_通訊軟體.py            # 通訊軟體 Bot（v2）
│   └── 7_自動化任務.py          # 自動化任務（v2）
├── lib/
│   ├── paths.py                # 跨平台路徑工具
│   └── skills.py               # Skills CRUD 邏輯
├── install.sh / install.ps1    # 安裝腳本
├── start.sh / start.bat        # 啟動腳本
└── requirements.txt            # Python 依賴
```

## 🔧 進階設定

更改 port（預設 8501）：
```bash
AI_HUB_PORT=9999 bash start.sh
```

## 📍 檔案位置

| 項目 | 位置 |
|------|------|
| Skills | `~/.claude/skills/<skill-name>/SKILL.md` |
| Claude Code 設定 | `~/.claude/` |
| 管家設定 | `~/ai-hub/config.json`（v2） |

## 🤝 貢獻

歡迎 PR 和 Issue！如果你有好的 Skill 範本想分享，也歡迎提交。

## 📄 授權

MIT License
