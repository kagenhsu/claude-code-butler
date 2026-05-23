"""🤖 雲端模型 — 占位頁（v1）"""
import streamlit as st

st.set_page_config(page_title="雲端模型 | AI Hub", page_icon="🤖", layout="wide")
st.title("🤖 雲端模型")
st.caption("管理 Claude / OpenAI / Gemini 等雲端 LLM 的 API Key 與預設設定")

st.info("🚧 **Coming Soon**\n\nv2 將提供：")
st.markdown(
    """
    - 🔑 各家 API Key 安全儲存（加密）
    - 🧪 一鍵連線測試
    - 📊 各模型 Token 使用量 / 費用追蹤
    - 🎯 為不同任務設定預設模型
    """
)

st.divider()
st.subheader("規劃中的模型列表")

models = [
    ("Anthropic", "Claude Opus 4.7", "claude-opus-4-7", "🟣"),
    ("Anthropic", "Claude Sonnet 4.6", "claude-sonnet-4-6", "🟣"),
    ("Anthropic", "Claude Haiku 4.5", "claude-haiku-4-5", "🟣"),
    ("OpenAI", "GPT-4o", "gpt-4o", "🟢"),
    ("OpenAI", "GPT-4o mini", "gpt-4o-mini", "🟢"),
    ("Google", "Gemini 2.5 Pro", "gemini-2.5-pro", "🔵"),
]

for vendor, name, model_id, emoji in models:
    with st.container(border=True):
        c1, c2, c3 = st.columns([1, 4, 2])
        with c1:
            st.markdown(f"### {emoji}")
        with c2:
            st.markdown(f"**{name}**")
            st.caption(f"{vendor} · `{model_id}`")
        with c3:
            st.button("設定", key=f"cfg-{model_id}", disabled=True, use_container_width=True)
