"""💬 對話沙盒 — 占位頁（v1）"""
import streamlit as st

st.set_page_config(page_title="對話沙盒 | AI Hub", page_icon="💬", layout="wide")
st.title("💬 對話沙盒")
st.caption("在面板內直接跟任一模型對話，比較不同模型的回答")

st.info("🚧 **Coming Soon**\n\nv2 將提供：")
st.markdown(
    """
    - 💬 多模型並排對話（同一個 prompt 餵給 Claude / GPT / Gemini / Ollama）
    - 🗂️ 對話歷史儲存與搜尋
    - 📋 一鍵套用 Prompt 庫的範本
    - 📁 拖拉檔案進對話（圖片 / PDF / 程式碼）
    - 📤 匯出對話為 Markdown / JSON
    """
)

st.divider()

# 預覽 UI（disabled）
st.subheader("UI 預覽")
with st.container(border=True):
    cols = st.columns(3)
    for i, m in enumerate(["Claude Opus 4.7", "GPT-4o", "Llama 3.1 8B (本地)"]):
        with cols[i]:
            st.markdown(f"**{m}**")
            st.text_area(f"回應 #{i+1}", value="（尚未啟用）", height=200, disabled=True, key=f"preview-{i}")

    st.text_input("你的訊息", placeholder="輸入 prompt…", disabled=True)
    st.button("送出（disabled）", disabled=True, use_container_width=True)
