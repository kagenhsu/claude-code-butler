"""📱 通訊軟體整合 — 占位頁（v1）

讓你用手機 / 平板的 LINE、Telegram、Discord 等通訊軟體跟 AI Hub 對話
"""
import streamlit as st

st.set_page_config(page_title="通訊軟體 | AI Hub", page_icon="📱", layout="wide")
st.title("📱 通訊軟體整合")
st.caption("從手機 / 平板透過通訊軟體跟 AI 對話")

st.info("🚧 **Coming Soon**\n\nv2 將提供：")
st.markdown(
    """
    - 💚 **LINE Bot** — 在 LINE 內輸入訊息，AI 立即回覆（需配合 Cloudflare Tunnel）
    - ✈️ **Telegram Bot** — 最容易上手，5 分鐘建好（不需要 tunnel）
    - 🎮 **Discord Bot** — 加進 Server，全頻道都能對話
    - 📲 **WhatsApp**（透過 Meta 商業 API）
    - 🌐 **手機網頁版** — 透過 tunnel 直接在手機瀏覽器使用 AI Hub
    """
)

st.divider()

# 三大平台對照表
st.subheader("方案比較")

st.markdown(
    """
    | 平台 | 申請難度 | 需要 Tunnel | 適合場景 |
    |------|---------|------------|---------|
    | ✈️ Telegram | ⭐ 極簡 (找 @BotFather) | ❌ 不用 | 個人快速使用 |
    | 💚 LINE | ⭐⭐ 中（要 LINE Developers） | ✅ 要 | 台灣朋友共用 |
    | 🎮 Discord | ⭐⭐ 中 | 部分需要 | 團隊共用 |
    | 🌐 手機瀏覽器 | ⭐ 極簡 | ✅ 要 | 完整 UI |
    """
)

st.divider()

# 預覽 UI
st.subheader("UI 預覽")
with st.container(border=True):
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### 💚 LINE Bot")
        st.text_input("Channel Access Token", placeholder="貼上 LINE Developers 取得的 token", disabled=True)
        st.text_input("Channel Secret", placeholder="貼上 channel secret", disabled=True)
        st.text_input("Webhook URL（自動產生）", value="https://xxxx.trycloudflare.com/webhook/line", disabled=True)
        st.button("啟動 LINE Bot", disabled=True, use_container_width=True)

    with c2:
        st.markdown("#### ✈️ Telegram Bot")
        st.text_input("Bot Token", placeholder="從 @BotFather 取得", disabled=True)
        st.selectbox("使用模型", ["Claude Opus 4.7", "GPT-4o", "Gemini 2.5 Pro"], disabled=True)
        st.checkbox("允許群組對話", value=False, disabled=True)
        st.button("啟動 Telegram Bot", disabled=True, use_container_width=True)
