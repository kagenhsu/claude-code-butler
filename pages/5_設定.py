"""⚙️ 設定 — 占位頁（v1 顯示路徑資訊）"""
from __future__ import annotations

import platform
import sys
from pathlib import Path

import streamlit as st

from lib.paths import claude_dir, user_skills_dir, config_file

st.set_page_config(page_title="設定 | AI Hub", page_icon="⚙️", layout="wide")
st.title("⚙️ 設定")
st.caption("系統資訊、路徑、未來的 API Key 與預設模型")

# ── 系統資訊 ──────────────────────────────────────────────
st.subheader("🖥️ 系統資訊")
with st.container(border=True):
    c1, c2 = st.columns(2)
    with c1:
        st.write(f"**作業系統**：{platform.system()} {platform.release()}")
        st.write(f"**Python**：{sys.version.split()[0]}")
    with c2:
        st.write(f"**主機名稱**：{platform.node()}")
        st.write(f"**架構**：{platform.machine()}")

st.divider()

# ── 路徑 ──────────────────────────────────────────────
st.subheader("📁 路徑")
with st.container(border=True):
    st.write(f"**Home**：`{Path.home()}`")
    st.write(f"**Claude 目錄**：`{claude_dir()}`")
    st.write(f"**Skills 目錄**：`{user_skills_dir()}`")
    st.write(f"**AI Hub 設定檔（規劃中）**：`{config_file()}`")

st.divider()

# ── 未來功能 ──────────────────────────────────────────────
st.subheader("🔮 未來功能（v2）")
st.markdown(
    """
    - 🔑 API Key 管理（Anthropic / OpenAI / Google）— 加密儲存
    - 🎨 主題切換（淺色 / 深色 / 跟系統）
    - 🌐 語系（繁中 / 簡中 / 英文）
    - 🎯 預設模型設定
    - 📦 備份與還原（Skills、設定、Prompt 庫）
    """
)
