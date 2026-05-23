# 🧠 Claude Code 管家 (Claude Code Butler)

> 專為 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) 打造的本機圖形化管理介面。
> 不用記指令，打開瀏覽器就能管理 Skills、雲端模型、本地模型、對話比較。

![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20%7C%20Linux-blue)
![License](https://img.shields.io/badge/license-MIT-green)

---

## 這是什麼？

**Claude Code** 是 Anthropic 官方的 AI 程式助手，在終端機裡幫你寫程式、改檔案、跑指令。

**Claude Code 管家**是它的瀏覽器管理介面 — 把所有設定、模型、技能集中在一個網頁儀表板，讓你不用記指令就能操作一切。

---

## ✨ 功能一覽

| 功能 | 狀態 | 說明 |
|------|------|------|
| 📂 **技能管理** | ✅ 可用 | 建立/編輯/刪除 Skill，3 個現成範本一鍵建立，**從 GitHub 安裝 Skill（含自動安全檢查）** |
| 🤖 **雲端模型** | ✅ 可用 | 7 家 AI 廠商 API Key 管理，支援**訂閱制 + API Key 雙模式**，一鍵測試連線 |
| 💻 **本地模型** | ✅ 可用 | Ollama / LM Studio 偵測管理，一鍵下載模型，**CC Switch 整合** |
| 💬 **對話沙盒** | ✅ 可用 | 同一句話餵給最多 3 個模型，**並排比較回答** |
| ⚙️ **設定** | ✅ 可用 | 硬體規格偵測、任務容量估算、模型使用狀態、方案比較 |
| 🏠 **首頁儀表板** | ✅ 可用 | 即時顯示 Skills 數量、雲端連線、本地模型、硬體資訊、目前方案 |
| 📱 通訊軟體 | 🔜 v2 | LINE / Telegram / Discord Bot |
| 🤖 自動化任務 | 🔜 v2 | 監控 AI Agent 執行狀態與排程任務 |

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

Skill 是教 Claude Code 怎麼做某件事的 Markdown 檔案。建立後在 Claude Code 輸入 `/skill 名稱` 就會觸發。

**功能：**
- ➕ 從零開始建立 Skill
- 📋 從 3 個現成範本一鍵建立（程式碼審查、Git 提交助手、測試產生器）
- 🌐 **從 GitHub 安裝 Skill** — 貼上 GitHub 連結，自動抓取內容
- 🛡️ **自動安全檢查** — 掃描 15 種危險指令模式（`rm -rf`、`curl|sh`、`sudo` 等），危險的會阻擋
- ✏️ 編輯 / 🗑️ 刪除現有 Skill
- 預覽 Skill 內容（渲染 + 原始碼）

**使用流程：**
```
管家網頁 → 技能管理 → 從範本建立 → 重啟 Claude Code → 輸入 /skill-名稱
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
| 🔷 **DeepSeek** | Free / Pro | DeepSeek-R1 / V3 |
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

### 💬 對話沙盒

> 「同一句話餵給不同 AI，並排比較回答」

- 從所有已設定的模型中選擇最多 **3 個**
- 輸入一句話，同時送出，並排顯示回答
- 每個回答顯示模型名稱和回應時間（⏱️）
- 支援所有已設定的雲端 API + Ollama 本地模型 + LM Studio
- 對話歷史保留在頁面中，可一鍵清除

**適合用來：**
- 比較不同模型的回答品質和速度
- 測試 Prompt 在各家模型的效果
- 選擇最適合你任務的模型

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

## 📦 搬到別台電腦

1. 把整個資料夾複製過去（**不要**複製 `.venv/`，目標電腦會自動重建）
2. 雙擊「安裝」
3. 完成

---

## 🗂️ 檔案結構

```
claude-code-butler/
├── 安裝.command / 安裝.bat       # 雙擊即可安裝（macOS / Windows）
├── 啟動.command / 啟動.bat       # 雙擊即可啟動（管家網頁 + Claude Code）
├── app.py                        # Streamlit 主入口（首頁儀表板）
├── pages/                        # 各功能頁面
│   ├── 1_技能管理.py              # Skill 管理 + GitHub 安裝
│   ├── 2_雲端模型.py              # 7 家廠商 API Key / 訂閱制管理
│   ├── 3_本地模型.py              # Ollama / LM Studio / CC Switch
│   ├── 4_對話沙盒.py              # 多模型並排對話比較
│   ├── 5_設定.py                  # 硬體規格 / 使用狀態 / 方案比較
│   ├── 6_通訊軟體.py              # 通訊軟體 Bot（v2）
│   └── 7_自動化任務.py            # 自動化任務（v2）
├── lib/
│   ├── paths.py                  # 跨平台路徑工具
│   ├── skills.py                 # Skills CRUD 邏輯
│   ├── github_skill.py           # GitHub Skill 抓取 + 安全檢查
│   ├── status.py                 # 系統狀態偵測（雲端/本地模型）
│   ├── hardware.py               # 硬體規格偵測 + 任務容量估算
│   ├── usage.py                  # Claude Code 使用量偵測
│   └── templates.py              # Skill 範本定義
├── assets/
│   └── style.css                 # 專業介面風格
├── install.sh / install.ps1      # 安裝腳本
├── start.sh / start.bat          # 啟動腳本
├── requirements.txt              # Python 依賴
└── LICENSE                       # MIT License
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
| Claude Code 設定 | `~/.claude/settings.json` |
| 管家設定（API Key 等） | `<專案目錄>/config.json` |
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
