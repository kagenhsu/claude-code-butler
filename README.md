# 🧠 Claude Code 管家 (Claude Code Butler)

> 專為 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 打造的本機圖形化管理介面。
> 不用記指令，打開瀏覽器就能管理 **Skills / 雲端模型 / 本地模型 / Hooks / MCP servers / 通訊軟體 bot / 自動化任務**，全部資料留在本機，API Key 加密存放。

![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## 這是什麼？

**Claude Code** 是 Anthropic 官方的 AI 程式助手，在終端機裡幫你寫程式、改檔案、跑指令。

**Claude Code 管家**是它的瀏覽器管理介面 — 把所有設定、模型、技能集中在一個網頁儀表板，讓你不用記指令就能操作一切。

---

## ✨ 功能一覽（9 個頁面，全部可用）

| 頁面 | 功能 |
|------|------|
| 🏠 **首頁儀表板** | Skills 數量、雲端連線、本地模型、今日對話、硬體摘要、Claude Code 版本與方案 |
| 📂 **技能管理** | **5 種來源安裝**：① GitHub（含集合 repo 如 `anthropics/skills` 自動列出全部 skill 勾選批次裝）② 任意 URL ③ 貼上內容 ④ 上傳 `.md` ⑤ 按名稱搜尋（本地 fuzzy + GitHub 熱門 fallback）— 安裝前自動安全檢查（攔 `rm -rf`、`curl \| sh` 等 15 種危險指令） |
| 💬 **對話沙盒** | 跟 AI 討論想法，確認後一鍵送到 **Claude 桌面版 / VS Code / Claude Code** 執行；上傳圖片 / 程式碼；多模型對話 |
| 🤖 **雲端模型** | **7 家** AI 廠商 API Key 管理（Anthropic / OpenAI / Google / MiniMax / DeepSeek / xAI / Mistral），支援**訂閱制 + API Key 雙模式**、一鍵測試連線；🔒 **API Key 全部加密儲存**（PBKDF2-HMAC-SHA256 + 本機主密鑰） |
| 💻 **本地模型** | Ollama / LM Studio 偵測管理，一鍵下載模型；**CC Switch 整合**（一鍵切換 Claude Code 後端）；7 個推薦模型依硬體標示能不能跑 |
| ⚙️ **設定** | 硬體規格偵測、任務容量估算、模型使用狀態、方案比較、**設定備份 / 還原**、明文 Key 一鍵遷移成加密 |
| 📱 **通訊軟體** | **Telegram + LINE bot** — 在手機 / 平板透過聊天介面跟 Claude 對話；完整教學（BotFather、LINE Developers、Cloudflare Tunnel）；subprocess 啟停 + log；白名單機制 |
| 🤖 **自動化任務** | **每日排程** + **專案任務** — 常駐 scheduler 跑 `claude -p`；支援「每天 HH:MM／每週幾 HH:MM／每 N 分鐘」；每次執行的 log 都保留；專案任務綁工作目錄、手動「立即執行」 |
| 🪝 **Hooks** | Claude Code 事件鉤子管理（PreToolUse / PostToolUse / Stop / SessionStart 等 8 事件）；**6 個範本**（攔 `rm -rf`、自動 format、Stop 桌面通知、稽核 Bash…）；bash syntax check + dry-run 測試 |
| 🔌 **MCP** | **新手友善卡片**：12 個官方常用 MCP server（filesystem / GitHub / git / sqlite / postgres / puppeteer / brave-search / slack / memory…），每張卡含 🛡️ 權限說明 / ⚠️ 風險等級 / 📦 依賴偵測 / 安全提醒；**搜尋功能**：本地 + npm registry（含週下載量排序）；**從 GitHub URL 抓 README 自動解析設定**；官方目錄掃描；全域 + 專案範圍切換 |

> 💡 **資料安全**：所有設定、Skills、API Key 都只存在你自己的電腦（`~/.claude/`、專案目錄），不會上傳任何雲端。API Key 加密寫入；主密鑰權限 `0600` 只有你能讀。

---

## 🚀 安裝方式

### 零基礎安裝（推薦）

完全不需要事先安裝任何東西，腳本會自動幫你裝好所有依賴：

> Git → Python → Node.js → Claude Code CLI → VS Code → Claude Code VS Code 擴充套件 → Streamlit

#### macOS

在 Finder 中找到資料夾，**雙擊 `安裝.command`** 即可。

或在終端機輸入：
```bash
bash install.sh
```

#### Windows

在檔案總管中找到資料夾，**雙擊 `安裝.bat`** 即可。

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

---

## ▶️ 日常使用

安裝完成後，每次要用只需要：

| 平台 | 方法一：雙擊 | 方法二：指令 |
|------|-------------|-------------|
| macOS / Linux | 雙擊 `啟動.command` | `bash start.sh` |
| Windows | 雙擊 `啟動.bat` | `start.bat` |

啟動後會同時開啟：
1. **瀏覽器** — 管家網頁（`http://localhost:8501`）
2. **終端機** — Claude Code CLI，直接開始跟 AI 對話

---

## 📖 各功能詳細說明

### 📂 技能管理

> 「教 Claude Code 做特定任務的腳本」

Skill 是教 Claude Code 怎麼做某件事的 Markdown 檔案。建立後在 Claude Code 輸入 `/名稱` 即可觸發，不需要重啟。

**功能：**
- 🌐 **從 GitHub 安裝 Skill** — 貼上 GitHub 連結，自動抓取內容（最推薦）
- 📋 從 3 個現成範本一鍵建立（程式碼審查、Git 提交助手、測試產生器）
- ➕ 從零開始建立 Skill
- 🛡️ **自動安全檢查** — 掃描 15 種危險指令模式（`rm -rf`、`curl|sh`、`sudo` 等），危險的會阻擋
- ✏️ 編輯 / 🗑️ 刪除現有 Skill
- 預覽 Skill 內容（渲染 + 原始碼）

**使用流程：**
```
管家網頁 → 技能管理 → 從 GitHub 安裝 / 從範本建立 / 從零開始 → 在 Claude Code 輸入 /名稱
```

---

### 💬 對話沙盒

> 「跟 AI 討論想法，確認好了再送到工具去執行」

**核心工作流程：**
```
💬 對話沙盒（討論）→ 確認方案 → 🖥️ Claude 桌面版 / 📝 VS Code / 💻 Claude Code
```

**為什麼不直接在 Claude Code 討論？**
- 對話沙盒不會改檔案，純聊天無風險
- 可用便宜模型討論（Haiku / GPT-4o mini / DeepSeek），省主力模型額度
- 可上傳圖片、程式碼、文件輔助討論

**頂部工具列（不佔側邊欄）：**

| 按鈕 | 功能 |
|------|------|
| 模型選擇 | 選擇對話模型（含訂閱制的 Claude Code） |
| ⚙️ 設定 | 角色指令、回應長度、比較模式 |
| 📎 附件 | 上傳圖片（PNG/JPG）或程式碼檔案 |
| 🗑️ 新對話 | 清除對話重新開始 |

**每個 AI 回答下方的動作按鈕：**

| 按鈕 | 動作 |
|------|------|
| 🚀 下一步 | 展開送出面板，選擇要送到哪裡 |
| 🖥️ 桌面版 | 複製到剪貼簿 + 開啟 Claude Desktop（適合 Cowork 深入規劃） |
| 📝 VS Code | 存成任務檔 + 開啟 VS Code（適合邊看程式碼邊修改） |
| 📋 複製 | 複製回答到剪貼簿 |

**「🚀 下一步」送出面板（點按鈕後展開在對話區域上方）：**

| 分頁 | 說明 |
|------|------|
| 🖥️ Claude 桌面版 | 一鍵開啟 + 複製，用 Cowork 功能做更詳細的規劃 |
| 📝 VS Code | 存成任務檔 + 開啟 VS Code，在 IDE 內用 Claude Code 擴充套件執行 |
| 💻 Claude Code CLI | 存成任務檔或複製 `claude -p` 指令到終端機 |
| 📥 儲存 / 下載 | 下載為 Markdown 或純文字檔案 |

**使用量狀態列（即時顯示在對話區上方）：**
```
💬 對話：3 則　📡 API 呼叫：3 次　⏱️ 總耗時：8.2s　💳 Max 20x — 20 倍速率上限
```

---

### 🤖 雲端模型

> 「管理你的 AI 服務帳號」

支援 **7 家 AI 廠商**，每家都能選擇**訂閱制**或 **API Key** 兩種使用方式：

| 廠商 | 訂閱方案 | 模型 |
|------|----------|------|
| 🟣 **Anthropic** | Free / Pro / Max 5x / Max 20x | Claude Opus 4.7 / Sonnet 4.6 / Haiku 4.5 |
| 🟢 **OpenAI** | Free / Plus / Pro | GPT-4o / GPT-4o mini / o3 |
| 🔵 **Google** | Free / AI Premium | Gemini 2.5 Pro / Flash |
| 🟡 **MiniMax** | Free / Hailuo Pro / Unlimited | MiniMax-Text-01 / M1 |
| 🔷 **DeepSeek** | Free / Pro | DeepSeek-R1 / V3-0324 |
| ⚫ **xAI** | Free / Premium / SuperGrok | Grok 3 / Grok 3 mini |
| 🟠 **Mistral** | Free / Le Chat Pro | Mistral Large / Codestral |

**每家廠商都有：**
- 🔄 訂閱制方案選擇 / 🔑 API Key 輸入
- 💾 儲存到本機（不會上傳）
- 🧪 一鍵測試連線
- 🗑️ 移除已儲存的設定
- 🔗 快速連結：官網、訂閱方案、API Key 申請、API 定價、API 文件

---

### 💻 本地模型

> 「在你的電腦上離線跑 AI」

**Ollama / LM Studio 管理：**
- 🔍 自動偵測安裝狀態與版本
- 📋 列出所有已下載的模型（名稱、大小、量化等級、類型）
- 📥 輸入名稱一鍵下載新模型
- 🗑️ 一鍵移除模型
- 🖥️ LM Studio 伺服器啟動/停止控制

**推薦模型：**

7 個熱門本地模型，依據你的硬體自動標示能不能跑：

| 模型 | 來源 | 記憶體需求 |
|------|------|-----------|
| Llama 3.1 8B | Meta | 8 GB |
| Qwen 2.5 7B | Alibaba | 8 GB |
| Gemma 2 9B | Google | 8 GB |
| Qwen 2.5 Coder 7B | Alibaba | 8 GB |
| DeepSeek R1 8B | DeepSeek | 8 GB |
| Phi-4 14B | Microsoft | 16 GB |
| Llama 3.1 70B | Meta | 48 GB |

每個模型都有 **🦙 Ollama 安裝** 和 **🎬 LM Studio 安裝** 兩個按鈕。

**🔀 CC Switch — 一鍵切換 Claude Code 的 AI 後端：**

[CC Switch](https://github.com/farion1231/cc-switch) 是第三方桌面工具，讓你用圖形介面切換 Claude Code 使用的模型後端。

管家內建：
- 📥 自動安裝 CC Switch（macOS 自動下載 DMG 安裝）
- 🚀 一鍵開啟 CC Switch
- ⚙️ 不裝 CC Switch 也能手動切換後端：
  - ☁️ Anthropic（官方）
  - 🎬 LM Studio（本地）
  - 🦙 Ollama（本地）
  - 🔷 DeepSeek
  - 🟢 OpenAI
  - 🌐 OpenRouter

---

### ⚙️ 設定

> 「了解你的電腦能力和 AI 使用狀態」

**硬體規格偵測：**
- CPU 型號 / 核心數
- 記憶體總量 / 可用量 / 使用率進度條
- GPU 型號 / 核心數
- 磁碟總量 / 可用空間 / 使用率進度條

**自動化任務容量估算：**
- 依硬體計算可同時執行幾個 Claude Code 任務
- 顯示瓶頸是 CPU 還是記憶體

**模型使用狀態：**
- 目前使用的模型、等級、上下文長度
- 推測的訂閱方案
- 今日 Session 數 / 對話次數

**方案比較表：**
- Free / Pro / Max 5x / Max 20x 完整比較

---

### 🏠 首頁儀表板

即時總覽所有狀態：

| 區塊 | 顯示內容 |
|------|----------|
| 📂 Skills | 已建立的 Skill 數量 |
| 🤖 雲端模型 | 已連接 / 總數（7 家） |
| 💻 本地模型 | Ollama + LM Studio 模型數量 |
| 💬 今日對話 | 今日在 Claude Code 的對話次數 |
| 🤖 可同時任務 | 依硬體估算的並行任務數 |
| Claude Code 資訊 | 版本、目前模型、方案、雲端連線狀態 |
| 硬體摘要 | CPU / 記憶體 / GPU / 磁碟一行摘要 |

---

### 📱 通訊軟體

> 「從手機 / 平板用 LINE 或 Telegram 跟 Claude 對話」

**支援平台：**
- ✈️ **Telegram Bot** — 申請最簡單，30 秒拿 token，不需要 tunnel（長輪詢）
- 💚 **LINE Bot** — 台灣親友最常用，需要 Cloudflare Tunnel 接 webhook

**每個平台都有：**
- 完整申請步驟（含可複製的指令、申請連結）
- Token 加密儲存（複用 API Key 加密機制）
- 啟動 / 停止 / 即時 log 檢視
- 白名單機制（chat_id / userId）— 沒授權的人傳訊息會被自動拒絕
- 故障排除文件（按鈕沒反應、訊息沒回、tunnel 網址變動…）

**架構：**
- bot 是獨立 subprocess（脫離 Streamlit），關閉管家不影響 bot 運行
- PID 與 log 存 `~/.claude/bots/`

---

### 🤖 自動化任務

> 「讓 Claude Code 定期幫你做事，或對某個專案一鍵跑流程」

**兩種任務：**

| 類型 | 用法 | 範例 |
|------|------|------|
| ⏰ **每日排程** | 設定時間後自動觸發 | 每天 09:00 整理昨天 git log + 寄 Telegram |
| 📁 **專案任務** | 綁某個工作目錄，手動「立即執行」 | 對 `~/work/proj-a` 跑「全專案程式碼審查」 |

**核心機制：**
- 任務內容是一段 prompt + 工作目錄，AI Hub 會背景跑 `claude -p "<你的 prompt>"`
- 排程支援：**每天 HH:MM** / **每週幾 HH:MM** / **每 N 分鐘**
- 常駐 scheduler 子程序每 30 秒檢查一次
- 每次執行的 log 都單獨保存（`~/.claude/aihub_tasks/<id>/<timestamp>.log`）
- 歷史紀錄（最近 200 筆）含成敗 / 耗時 / log 路徑

---

### 🪝 Hooks

> 「在 Claude Code 觸發特定事件時自動跑 shell 指令」

**支援 8 種事件：**

| 事件 | 觸發時機 |
|------|----------|
| `PreToolUse` | Claude 即將呼叫工具前（可 `exit 2` 阻止） |
| `PostToolUse` | 工具呼叫結束後（適合自動 format / lint） |
| `UserPromptSubmit` | 你送出 prompt 時（stdout 會注入到 Claude 視角） |
| `Stop` / `SubagentStop` | Assistant / Subagent 結束時 |
| `Notification` | Claude Code 推送通知時 |
| `SessionStart` | 新 session 啟動時 |
| `PreCompact` | Context 壓縮前 |

**6 個內建範本：**
- 🔔 任務完成跳 macOS 通知（Stop）
- 📜 稽核所有 Bash 指令（PreToolUse）
- 🛡️ 攔截危險的 `rm -rf` 指令
- 🎨 寫完 Python 檔自動跑 ruff format
- 🌿 SessionStart 印 git status
- 🔐 禁止改 `.env` / `*.pem` / `*.key`

**支援範圍：**
- 全域 `~/.claude/settings.json`
- 專案 `<project>/.claude/settings.json`

**安全測試：**
- 🔍 bash syntax check（`bash -n`）
- 🧪 dry-run（直接 `bash -c` 跑一次看 exit code / stdout / stderr）

---

### 🔌 MCP — 給 Claude 裝外掛

> 「MCP (Model Context Protocol) 是 Anthropic 開源的協定，讓 Claude 能連到外部資料和工具」

**新手友善設計：**
首頁就是「我想讓 Claude 做什麼」的卡片，分兩個分頁：

| 👤 一般使用 | 👨‍💻 開發者 |
|---|---|
| 📁 整理檔案 (filesystem) | 🐙 GitHub (issue / PR 操作) |
| 🦁 上網搜尋 (brave-search) | 🌿 本機 Git (status / log / diff) |
| 🧠 跨對話記憶 (memory) | 🗄️ SQLite |
| 🌐 抓網頁 (fetch) | 🐘 Postgres (唯讀) |
| 🕐 時間／時區 (time) | 🎭 Puppeteer 瀏覽器自動化 |
| | 💭 Sequential Thinking |
| | 💬 Slack |

**每張卡片必含的資安資訊：**
- 🛡️ **權限**：一句話講清楚 Claude 拿到後能存取什麼
- ⚠️ **風險等級**：🟢 低 / 🟡 中 / 🔴 高
- 📦 **依賴**：缺哪個工具直接顯示 ❌ + 安裝指令（`brew install ...`）

**進階搜尋（收在 expander）：**
- 關鍵字搜尋（內建 + npm registry，週下載量排序）
- 官方目錄掃描（`modelcontextprotocol/servers` repo）
- **從 GitHub URL 抓 README 自動解析** — 給任意 MCP server repo 連結，自動找出 `mcpServers` JSON 區塊或 npx 安裝指令
- 手動 / 貼 JSON

**連線測試：**
真正 spawn server 並送 MCP `initialize` JSON-RPC 看回應，能驗證指令是否真的能跑。

**範圍：**
- 全域 `~/.claude.json` 的 `mcpServers`（只動這 key，其他欄位原樣保留；每次寫入自動 backup 5 份）
- 專案 `<project>/.mcp.json`（可 commit 到 git，給團隊共用）

---

## 📦 搬到別台電腦

1. 把整個資料夾複製過去（**不要**複製 `.venv/`，目標電腦會自動重建）
2. 雙擊「安裝」
3. 完成

---

## 🗂️ 檔案結構

```
claude-code-butler/
├── 安裝.command / 安裝.bat        # 雙擊即可安裝（macOS / Windows）
├── 啟動.command / 啟動.bat        # 雙擊即可啟動（管家網頁 + Claude Code）
├── app.py                         # Streamlit 主入口（首頁儀表板）
├── pages/                         # 9 個功能頁面
│   ├── 1_技能管理.py               # Skills：5 種來源安裝 + 安全檢查
│   ├── 2_對話沙盒.py               # 跟 AI 討論想法 → 送到桌面版／VS Code／CLI
│   ├── 3_雲端模型.py               # 7 家廠商 API Key（加密）／訂閱制
│   ├── 4_本地模型.py               # Ollama / LM Studio / CC Switch
│   ├── 5_設定.py                   # 硬體規格／使用狀態／備份還原／方案比較
│   ├── 6_通訊軟體.py               # Telegram + LINE bot 管理
│   ├── 7_自動化任務.py             # 每日排程 + 專案任務 + scheduler
│   ├── 8_Hooks.py                  # Claude Code hooks 管理
│   └── 9_MCP.py                    # MCP servers 管理（卡片式 + 進階）
├── bots/                          # 獨立 worker（subprocess 啟動，脫離 Streamlit）
│   ├── telegram_worker.py          # Telegram 長輪詢 bot
│   ├── line_worker.py              # LINE webhook bot（含 HMAC 驗章）
│   └── scheduler.py                # 每日任務排程 worker
├── lib/                           # 核心模組
│   ├── paths.py                    # 跨平台路徑工具
│   ├── ui.py / nav.py / theme.py   # 共用 UI 元件 / 頂部導覽 / 主題
│   ├── crypto.py                   # PBKDF2-HMAC-SHA256 加密
│   ├── secrets_store.py            # 加密 API Key／token 儲存
│   ├── backup.py                   # 設定備份／還原
│   ├── llm.py                      # 統一 LLM 分派器（4 家 + Claude Code CLI）
│   ├── skills.py / templates.py    # Skills CRUD 與範本
│   ├── github_skill.py             # GitHub repo / 集合 repo 探索（Trees API）
│   ├── install_skill.py            # 通用 skill 解析（URL / paste / file）
│   ├── skill_directory.py          # Skill 名稱搜尋（本地 + GitHub）
│   ├── bot_runner.py               # subprocess 管理（PID／log）
│   ├── task_store.py               # 自動化任務 CRUD
│   ├── task_runner.py              # 任務執行（呼 claude -p）
│   ├── task_runner_cli.py          # 背景執行入口（python -m）
│   ├── hooks_store.py              # Claude Code hooks 讀寫 + 範本 + 測試
│   ├── mcp_store.py                # MCP servers CRUD + 連線測試
│   ├── mcp_directory.py            # MCP 範本 + 搜尋 + npm 下載量 + GitHub 抓取
│   ├── status.py                   # 系統狀態偵測（雲端／本地模型）
│   ├── hardware.py                 # 硬體規格偵測 + 任務容量估算
│   └── usage.py                    # Claude Code 使用量偵測
├── assets/
│   └── style.css                  # HUD 戰術風格
├── .streamlit/config.toml         # Streamlit 主題與行為設定
├── install.sh / install.ps1       # 安裝腳本
├── start.sh / start.bat           # 啟動腳本
├── requirements.txt               # Python 依賴（僅 streamlit）
└── LICENSE                        # MIT License
```

---

## 🔧 進階設定

更改 port（預設 8501）：
```bash
AI_HUB_PORT=9999 bash start.sh
```

---

## 📍 檔案位置

| 項目 | 位置 |
|------|------|
| Skills | `~/.claude/skills/<skill-name>/SKILL.md` |
| Claude Code 設定（含 hooks） | `~/.claude/settings.json` |
| Claude Code MCP servers | `~/.claude.json` 的 `mcpServers` 區塊 |
| 專案層 hooks / MCP / Skills | `<project>/.claude/settings.json`、`<project>/.mcp.json` |
| 管家設定（API Key 等，已 git-ignore） | `<專案目錄>/config.json` |
| API Key 加密主密鑰（權限 0600） | `~/.claude/.aihub_secret` |
| 自動化任務定義 | `~/.claude/aihub_tasks.json` |
| 自動化任務 log | `~/.claude/aihub_tasks/<task_id>/<timestamp>.log` |
| Bot worker（Telegram / LINE / scheduler）PID 與 log | `~/.claude/bots/<name>.pid` / `<name>.log` |
| 設定備份歷史 | `~/.claude/aihub_backups/` |
| Skill 來源快取（24h TTL） | `~/.claude/cache/skill_directory_*.json` |
| MCP 官方目錄快取（24h TTL） | `~/.claude/cache/mcp_official_directory.json` |
| 本地模型（LM Studio） | `~/.lmstudio/models/` |

---

## 🤝 貢獻

歡迎 PR 和 Issue！

- 有好的 **Skill 範本**想分享？歡迎提交
- 發現 **Bug**？請開 Issue
- 想加新的 **AI 廠商**？歡迎 PR

---

## 📄 授權

MIT License
