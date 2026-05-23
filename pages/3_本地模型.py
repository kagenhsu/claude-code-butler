"""💻 本地模型 — 占位頁（v1）"""
import streamlit as st

st.set_page_config(page_title="本地模型 | AI Hub", page_icon="💻", layout="wide")
st.title("💻 本地模型")
st.caption("管理 Ollama / LM Studio 等本地 LLM")

st.info("🚧 **Coming Soon**\n\nv2 將提供：")
st.markdown(
    """
    - 🔍 自動偵測本機已安裝的 Ollama / LM Studio
    - 📦 一鍵下載 / 移除模型
    - ▶️ 啟動 / 停止本地推論服務
    - 💾 顯示模型大小、量化等級
    - 🧠 RAM / VRAM 使用量監控
    """
)

st.divider()

# 偵測 Ollama 是否安裝（不啟動，只看是否存在）
import shutil

ollama_path = shutil.which("ollama")
lmstudio_path = shutil.which("lms")  # LM Studio CLI

c1, c2 = st.columns(2)
with c1:
    with st.container(border=True):
        st.markdown("### 🦙 Ollama")
        if ollama_path:
            st.success(f"✅ 已安裝：`{ollama_path}`")
        else:
            st.warning("❌ 未偵測到。安裝：https://ollama.com")

with c2:
    with st.container(border=True):
        st.markdown("### 🎬 LM Studio")
        if lmstudio_path:
            st.success(f"✅ 已安裝（CLI）：`{lmstudio_path}`")
        else:
            st.warning("❌ 未偵測到 CLI。下載：https://lmstudio.ai")
