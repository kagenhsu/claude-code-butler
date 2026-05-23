"""Claude Code 管家 — 你的 AI 助手管理中心

Streamlit 主入口（首頁 Dashboard）
左側自動產生側邊欄，列出 pages/ 底下所有頁面。
"""
from __future__ import annotations

import streamlit as st

from pathlib import Path

from lib.paths import claude_dir, user_skills_dir
from lib.skills import list_skills
from lib.status import detect_status
from lib.hardware import detect_hardware, estimate_task_capacity
from lib.usage import detect_usage

STYLE_CSS = (Path(__file__).parent / "assets" / "style.css").read_text()

st.set_page_config(
    page_title="Claude Code 管家",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(f"<style>{STYLE_CSS}</style>", unsafe_allow_html=True)

# ── 側邊欄：新手指南 ──────────────────────────────────────
with st.sidebar:
    st.markdown("### 🎓 新手指南")
    with st.expander("第一次使用？點我看 3 分鐘導覽", expanded=False):
        st.markdown(
            """
            **Claude Code 管家是什麼？**
            專為 Claude Code 打造的本機網頁管理介面。

            **你會用到的頁面**：
            1. **📂 Skills** — 教 Claude 做特定任務（最常用）
            2. **🤖 雲端模型** — 設定 OpenAI/Claude API（v2）
            3. **💻 本地模型** — 管 Ollama 等本地模型（v2）
            4. **💬 對話沙盒** — 比較不同 AI 回答（v2）
            5. **⚙️ 設定** — 系統資訊
            6. **📱 通訊軟體** — 用 LINE/Telegram 跟 AI 對話（v2）
            7. **🤖 自動化任務** — 看 agent 在做什麼、排程任務（v2）

            **小白起手式**：點側邊欄『📂 Skills』→ 選一個範本一鍵建立 → 在 Claude Code 輸入 `/skill 名稱` 就會啟動！
            """
        )

    st.divider()
    st.caption("💡 提示：所有頁面都有 ❓ 圖示，hover 上去看詳細說明。")

# ── 主畫面 ──────────────────────────────────────────────
st.title("🧠 Claude Code 管家")
st.caption("你的 AI 助手管理中心 — 管理 Skills、雲端與本地大語言模型")

# 偵測系統狀態
status = detect_status()
hw_spec = detect_hardware()
task_cap = estimate_task_capacity(hw_spec)
usage = detect_usage()

try:
    skills = list_skills()
    skill_count = len(skills)
except Exception:
    skill_count = 0

if skill_count == 0:
    st.success(
        "👋 **歡迎使用 Claude Code 管家！** 這是你第一次用，建議從建立第一個 Skill 開始 → "
        "點側邊欄的「**技能管理**」進入，有 3 個現成範本可以一鍵建立。"
    )

# ── 狀態總覽 ──────────────────────────────────────────────
st.subheader("📊 狀態總覽")

cloud_connected = sum(1 for m in status.cloud_models if m.status == "已連接")
cloud_total = len(status.cloud_models)

col1, col2, col3 = st.columns(3)
col4, col5, col6 = st.columns(3)

with col1:
    st.metric("📂 Skills", skill_count, help="你建立的 Claude Code skill 數量（位置：~/.claude/skills/）")
with col2:
    st.metric(
        "🤖 雲端模型",
        f"{cloud_connected} / {cloud_total}",
        help="已連接的雲端 LLM 數量",
    )
with col3:
    st.metric(
        "💻 本地模型",
        status.local_model_count,
        help="已安裝的本地 LLM 數量（透過 Ollama 偵測）",
    )
with col4:
    st.metric("💬 今日對話", usage.history_entries_today, help="今日在 Claude Code 的對話次數")
with col5:
    st.metric(
        "🤖 可同時任務",
        f"{task_cap.max_concurrent} 個",
        help=f"依據硬體估算（瓶頸：{task_cap.bottleneck}）",
    )
with col6:
    st.metric("📱 通訊軟體", "—", help="連接的 Bot 數量（v2 才會啟用）")

# ── Claude Code 資訊 ──────────────────────────────────────
with st.container(border=True):
    cc1, cc2, cc3, cc4 = st.columns(4)
    with cc1:
        if status.claude_code_installed:
            st.markdown(f"✅ **Claude Code**：`{status.claude_code_version}`")
        else:
            st.markdown("❌ **Claude Code**：未安裝")
    with cc2:
        st.markdown(f"🧠 **模型**：{usage.model_display}")
    with cc3:
        st.markdown(f"💳 **方案**：{usage.plan_name}")
    with cc4:
        labels = [f"{'✅' if m.status == '已連接' else '⬜'} {m.name}" for m in status.cloud_models]
        st.markdown("**雲端**：" + "　".join(labels))

# ── 硬體摘要 ──
with st.container(border=True):
    hw1, hw2, hw3, hw4 = st.columns(4)
    with hw1:
        st.markdown(f"💻 **CPU**：{hw_spec.cpu_name}（{hw_spec.cpu_cores} 核心）" if hw_spec.cpu_name else f"💻 **CPU**：{hw_spec.cpu_cores} 核心")
    with hw2:
        st.markdown(f"🧮 **記憶體**：{hw_spec.ram_total_gb} GB（可用 {hw_spec.ram_available_gb} GB）")
    with hw3:
        st.markdown(f"🎮 **GPU**：{hw_spec.gpu_name}（{hw_spec.gpu_cores} 核心）" if hw_spec.gpu_name else "🎮 **GPU**：未偵測到")
    with hw4:
        st.markdown(f"💾 **磁碟**：{hw_spec.disk_free_gb:.0f} GB 可用")

# ── 本地模型清單 ──
if status.local_models:
    with st.expander(f"💻 本地模型清單（{status.local_model_count} 個）", expanded=False):
        for m in status.local_models:
            st.write(f"- `{m}`")

st.divider()

# ── 快速入口 ──────────────────────────────────────────────
st.subheader("🚀 快速入口")

c1, c2, c3 = st.columns(3)
with c1:
    with st.container(border=True):
        st.markdown(
            """
            ### 📂 Skills 管理
            建立、編輯、刪除你在 Claude Code 用的 skill。
            **適合**：寫教 Claude 怎麼做事的範本
            """
        )
        st.page_link("pages/1_技能管理.py", label="前往 技能管理 →", icon="📂")

with c2:
    with st.container(border=True):
        st.markdown(
            """
            ### 📱 通訊軟體
            從手機、平板透過 LINE / Telegram 跟 AI 對話。
            **適合**：在外面也想用 Claude 的人（v2）
            """
        )
        st.page_link("pages/6_通訊軟體.py", label="前往 通訊軟體 →", icon="📱")

with c3:
    with st.container(border=True):
        st.markdown(
            """
            ### ⚙️ 設定
            管理 API Key、預設模型、外觀偏好。
            **適合**：需要看路徑或系統資訊時
            """
        )
        st.page_link("pages/5_設定.py", label="前往 設定 →", icon="⚙️")

st.divider()

# ── 名詞解釋（新手友善） ──────────────────────────────────
with st.expander("📖 名詞解釋（看不懂的詞點這裡）", expanded=False):
    st.markdown(
        """
        | 名詞 | 解釋 |
        |------|------|
        | **Skill** | 教 Claude Code 做某件特定事情的「腳本檔」，例如「程式碼審查」。建立後可在 Claude Code 用 `/skill 名稱` 觸發。 |
        | **Claude Code** | Anthropic 官方的 CLI 工具，在終端機跟 Claude 對話、改檔案、跑指令。 |
        | **API Key** | 你跟 OpenAI 或 Anthropic 註冊後拿到的「通行證」，讓 Claude Code 管家能代你呼叫他們的 AI。 |
        | **Ollama** | 一套可以在你電腦上跑開源 LLM（如 Llama）的工具，**完全離線**。 |
        | **Cloudflare Tunnel** | 把你電腦上的服務安全地暴露給外部網路，用來接通 LINE Bot 之類的 webhook。 |
        | **Frontmatter** | Markdown 檔案最上方用 `---` 包起來的設定區（像名稱、描述），給程式讀取用。 |
        """
    )

with st.expander("ℹ️ 系統資訊", expanded=False):
    st.write(f"**Claude Code 目錄**：`{claude_dir()}`")
    st.write(f"**Skills 目錄**：`{user_skills_dir()}`")
    st.write("**版本**：v0.1.0")
