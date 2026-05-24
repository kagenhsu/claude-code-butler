"""📱 通訊軟體整合 — 把 AI Hub 接到 LINE / Telegram。

使用者可以在自己常用的通訊軟體跟 AI 對話：
- ✈️ Telegram：申請最簡單，不用 tunnel，5 分鐘搞定
- 💚 LINE：台灣社交圈最常用，但需要 Cloudflare Tunnel 才能對外

每個 tab 都包含：為什麼用 → 申請步驟 → 啟動 → 故障排除。
"""
from __future__ import annotations

import streamlit as st

from lib import bot_runner, llm, secrets_store

st.set_page_config(page_title="通訊軟體 | Claude Code 管家", page_icon="📱", layout="wide")

from lib.ui import inject_style  # noqa: E402
from lib.nav import render_nav  # noqa: E402

inject_style(st)
render_nav()

st.title("📱 通訊軟體整合")
st.caption("把 AI Hub 接上你常用的通訊軟體，在手機 / 平板隨時跟模型對話")

# ── 開頭：先講為什麼要弄這個 ─────────────────────────────
with st.container(border=True):
    st.markdown(
        """
        ### 🤔 為什麼要做這個？

        平常你打開 AI Hub 都是在電腦前。但如果你想：

        - 🚶 **出門通勤時用手機問模型** — 不用開瀏覽器、不用記網址
        - 👥 **跟朋友分享 AI 能力** — 把朋友的 LINE / Telegram 加入白名單
        - 📲 **隨時隨地拍照、傳文字檔給 AI** —（未來會支援，目前只支援文字）

        就把 AI 接到 LINE 或 Telegram，這頁就是教你怎麼做。
        """
    )

# ── 模型選擇前置檢查 ─────────────────────────────────────
available = llm.available_models()
if not available:
    st.error(
        "❌ 還沒有任何可用的模型 — 請先到 [🤖 雲端模型](/雲端模型) 設定至少一個 API Key，"
        "或安裝 Claude Code CLI（會自動偵測到 `claude` 指令）"
    )
    st.stop()

st.caption(
    f"✅ 目前可用的模型：{', '.join(llm.display_name(m) for m in available)}"
)

st.divider()

tab_tg, tab_line = st.tabs(["✈️ Telegram Bot", "💚 LINE Bot"])


# ╔═════════════════════════════════════════════════════════╗
# ║ Telegram                                                ║
# ╚═════════════════════════════════════════════════════════╝
with tab_tg:
    st.markdown("### ✈️ 把 AI 接到 Telegram")
    st.caption("最容易上手的一個 — 只要找 @BotFather 拿個 Token，不需要任何網路設定。")

    # 為什麼用 Telegram
    with st.expander("✨ 為什麼選 Telegram？", expanded=False):
        st.markdown(
            """
            - **零網路設定** — Bot 主動去 Telegram 伺服器抓訊息（長輪詢），你電腦不用對外開洞
            - **跨平台** — Mac、iPhone、Android、網頁版完全同步
            - **申請快** — 跟 @BotFather 講幾句話，30 秒拿到 Token
            - **缺點** — 台灣朋友不一定有裝 Telegram
            """
        )

    # 申請步驟
    with st.expander("📝 怎麼拿到 Bot Token？（第一次使用必看）", expanded=True):
        st.markdown(
            """
            1. 在 Telegram 搜尋並聊天：[**@BotFather**](https://t.me/BotFather)
            2. 傳指令 `/newbot`
            3. 取一個 **顯示名稱**（中文 OK，例如「我的 AI 助手」）
            4. 取一個 **使用者名稱**（必須英數 + 底線、結尾要 `bot`，例如 `kagen_ai_bot`）
            5. BotFather 會回一串 Token，長得像：
               ```
               7891234567:AAFw1Mq...很長的隨機字串...
               ```
            6. **複製這串 Token，貼到下面的欄位**

            > 💡 想拿你自己的 chat_id 做白名單？跟你的 Bot 講一句話，然後打開：
            > `https://api.telegram.org/bot<你的Token>/getUpdates`，找 `"chat":{"id":xxx}`。
            """
        )

    st.markdown("#### ⚙️ 設定")
    saved_token = secrets_store.get_api_key("telegram_bot_token", include_env=False)

    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
        new_tg_token = st.text_input(
            "Bot Token",
            type="password",
            placeholder="貼上 BotFather 給的 token（例如 7891234567:AAFw...）",
            value="",
            key="tg-token-input",
            help="儲存後會加密寫入 config.json",
        )
    with col_t2:
        if st.button("💾 儲存 Token", key="tg-save-token", type="primary", use_container_width=True):
            if not new_tg_token.strip():
                st.error("請先貼 Token")
            else:
                secrets_store.set_api_key("telegram_bot_token", new_tg_token.strip())
                st.success("✅ 已加密儲存")
                st.rerun()

    if saved_token:
        st.caption(f"目前已儲存：`{secrets_store.mask_key(saved_token)}` 🔒")
    else:
        st.caption("尚未儲存 Token")

    tg_model = st.selectbox(
        "回覆使用的模型",
        available,
        format_func=llm.display_name,
        index=0,
        key="tg-model",
    )
    tg_system = st.text_area(
        "個性設定（system prompt，可選）",
        placeholder="例如：你是一位簡潔友善的繁體中文助理，回答盡量在 200 字內。",
        height=80,
        key="tg-system",
    )
    tg_allowed = st.text_input(
        "白名單 chat_id（可選，多個用逗號分隔，留空 = 任何人傳訊都會被回覆）",
        placeholder="例如：123456789, 987654321",
        key="tg-allowed",
    )

    st.markdown("#### 🚀 啟動 / 停止")
    tg_status = bot_runner.status("telegram")

    s1, s2, s3 = st.columns([1, 1, 2])
    with s1:
        start_disabled = tg_status["running"] or not saved_token
        start_help = (
            "已經在跑了" if tg_status["running"]
            else "請先儲存 Bot Token" if not saved_token
            else None
        )
        if st.button(
            "▶️ 啟動 Bot",
            key="tg-start",
            type="primary",
            use_container_width=True,
            disabled=start_disabled,
            help=start_help,
        ):
            res = bot_runner.start(
                "telegram",
                [bot_runner.python_executable(), "-m", "bots.telegram_worker"],
                env={
                    "BOT_TOKEN": saved_token,
                    "BOT_MODEL": tg_model,
                    "BOT_SYSTEM": tg_system,
                    "BOT_ALLOWED_CHATS": tg_allowed,
                    "PYTHONUNBUFFERED": "1",
                },
            )
            if res["ok"]:
                st.success(res["msg"])
            else:
                st.error(res["msg"])
            st.rerun()
    with s2:
        if st.button(
            "⏹️ 停止 Bot",
            key="tg-stop",
            use_container_width=True,
            disabled=not tg_status["running"],
        ):
            res = bot_runner.stop("telegram")
            st.info(res["msg"])
            st.rerun()
    with s3:
        if tg_status["running"]:
            st.success(f"🟢 執行中（PID {tg_status['pid']}）")
        else:
            st.info("🔴 未執行")

    with st.expander("📜 即時 log（最近 40 行）", expanded=tg_status["running"]):
        log_text = bot_runner.tail_log("telegram", 40) or "(尚無 log)"
        st.code(log_text, language="text")
        log_c1, log_c2 = st.columns([1, 5])
        with log_c1:
            if st.button("🔄 重新讀取", key="tg-refresh-log"):
                st.rerun()
        with log_c2:
            if st.button("🧹 清空 log", key="tg-clear-log"):
                bot_runner.clear_log("telegram")
                st.rerun()

    # 故障排除
    with st.expander("🆘 故障排除", expanded=False):
        st.markdown(
            """
            **Bot 啟動後立刻停了？**
            → 看上面 log，最常見原因是 Token 錯字（會出現 `getMe 失敗`）。

            **訊息傳出去但沒回應？**
            → 1) 確認 log 有看到「💬 ... 訊息內容」這行；
            　 2) 沒有的話可能是白名單擋掉了；
            　 3) 如果有看到但沒回，通常是模型 API Key 沒設或額度用完。

            **想在多台電腦切換？**
            → Telegram 一個 Token 只能有一個程式在跑長輪詢。在新電腦啟動前，先在舊電腦停掉。

            **怎麼讓 Bot 不亂回別人？**
            → 一定要設白名單。你的 chat_id 可以在 log 裡看到（傳一句話後就會印出）。
            """
        )


# ╔═════════════════════════════════════════════════════════╗
# ║ LINE                                                    ║
# ╚═════════════════════════════════════════════════════════╝
with tab_line:
    st.markdown("### 💚 把 AI 接到 LINE")
    st.caption("台灣最常用 — 但需要 Cloudflare Tunnel 讓 LINE 伺服器能連到你的電腦。")

    with st.expander("✨ 為什麼要弄 LINE？（也要看清楚成本）", expanded=False):
        st.markdown(
            """
            **好處：**
            - 台灣親友都在用 LINE，他們完全不用裝新 app
            - 可以邀請朋友一起用你的 AI

            **要付出的成本：**
            - 一定要 **Cloudflare Tunnel** 把網路打通（LINE 用 webhook、是「LINE 主動連你」）
            - LINE Developers 後台設定步驟比 Telegram 多
            - LINE 免費版每月「主動推播」訊息有上限，但「回覆使用者訊息」不算
            """
        )

    with st.expander("🔧 第一步：先裝 Cloudflare Tunnel", expanded=True):
        st.markdown(
            """
            這套工具會把你電腦的某個 port「打洞」到網際網路上，給你一條臨時 https 網址。

            **Mac 安裝（用 Homebrew）：**
            ```bash
            brew install cloudflared
            ```

            **驗證有沒有裝好：**
            ```bash
            cloudflared --version
            ```

            **稍後啟動 Bot 後**，再開一個終端機跑這行（port 8765 對應下面預設）：
            ```bash
            cloudflared tunnel --url http://localhost:8765
            ```
            執行後它會印出類似這樣的網址：
            ```
            https://prosperous-bear-1234.trycloudflare.com
            ```
            把這串網址 + `/webhook` 貼進 LINE Developers 後台 → 你的 bot 就通了。
            """
        )

    with st.expander("📝 第二步：到 LINE Developers 申請 Channel", expanded=False):
        st.markdown(
            """
            1. 打開 [**LINE Developers Console**](https://developers.line.biz/console/)，用 LINE 帳號登入
            2. 建一個 **Provider**（任意名稱，例如「個人測試」）
            3. 在 Provider 下建一個 **Messaging API Channel**：
               - Channel name：隨便（例如「我的 AI 助手」）
               - Channel description：隨便
               - Category / Subcategory：隨便
            4. 建好後到 **Basic settings** 頁：
               - 複製 **Channel secret**（10 多位英數）
            5. 切到 **Messaging API** 頁：
               - 滾到底，按「Issue」產生 **Channel access token (long-lived)**
               - 複製這串 token（長得像 `Bearer` 後面那段，幾百個字元）
            6. **同一個頁面**，找到「Webhook settings」：
               - 把上一步 Cloudflare Tunnel 給你的網址 + `/webhook` 貼進「Webhook URL」
               - 把「Use webhook」打開
               - 把「Auto-reply messages」**關掉**（不然 LINE 會自動回固定訊息）
            7. 拿手機掃 QR Code 加 Bot 好友，傳一句話試試
            """
        )

    st.markdown("#### ⚙️ 設定")

    saved_secret = secrets_store.get_api_key("line_channel_secret", include_env=False)
    saved_line_token = secrets_store.get_api_key("line_channel_token", include_env=False)

    c1, c2 = st.columns(2)
    with c1:
        new_secret = st.text_input(
            "Channel Secret",
            type="password",
            placeholder="從 Basic settings 複製",
            key="line-secret",
        )
        if st.button("💾 儲存 Secret", key="line-save-secret", use_container_width=True):
            if not new_secret.strip():
                st.error("請先貼 Secret")
            else:
                secrets_store.set_api_key("line_channel_secret", new_secret.strip())
                st.success("✅ 已加密儲存")
                st.rerun()
        if saved_secret:
            st.caption(f"已儲存：`{secrets_store.mask_key(saved_secret)}` 🔒")
        else:
            st.caption("尚未儲存")

    with c2:
        new_line_token = st.text_input(
            "Channel Access Token（long-lived）",
            type="password",
            placeholder="從 Messaging API 頁產生",
            key="line-token",
        )
        if st.button("💾 儲存 Token", key="line-save-token", use_container_width=True):
            if not new_line_token.strip():
                st.error("請先貼 Token")
            else:
                secrets_store.set_api_key("line_channel_token", new_line_token.strip())
                st.success("✅ 已加密儲存")
                st.rerun()
        if saved_line_token:
            st.caption(f"已儲存：`{secrets_store.mask_key(saved_line_token)}` 🔒")
        else:
            st.caption("尚未儲存")

    line_model = st.selectbox(
        "回覆使用的模型",
        available,
        format_func=llm.display_name,
        index=0,
        key="line-model",
    )
    line_system = st.text_area(
        "個性設定（system prompt，可選）",
        placeholder="例如：你是一位簡潔友善的繁體中文助理。",
        height=80,
        key="line-system",
    )

    line_col_a, line_col_b = st.columns(2)
    with line_col_a:
        line_port = st.number_input(
            "本機監聽 port",
            min_value=1024,
            max_value=65535,
            value=8765,
            step=1,
            key="line-port",
            help="改了之後，cloudflared 指令裡的 port 也要跟著改",
        )
    with line_col_b:
        line_allowed = st.text_input(
            "白名單 userId（可選）",
            placeholder="多個用逗號分隔，留空 = 任何人都能用",
            key="line-allowed",
            help="LINE userId 可以在 log 裡看到（前 8 碼會印出，需要完整 ID 時打開 log 檔看）",
        )

    st.markdown("#### 🚀 啟動 / 停止")
    line_status = bot_runner.status("line")
    ready = bool(saved_secret and saved_line_token)

    s1, s2, s3 = st.columns([1, 1, 2])
    with s1:
        start_help = (
            "已經在跑了" if line_status["running"]
            else "請先儲存 Secret 與 Token" if not ready
            else None
        )
        if st.button(
            "▶️ 啟動 Bot",
            key="line-start",
            type="primary",
            use_container_width=True,
            disabled=line_status["running"] or not ready,
            help=start_help,
        ):
            res = bot_runner.start(
                "line",
                [bot_runner.python_executable(), "-m", "bots.line_worker"],
                env={
                    "BOT_CHANNEL_SECRET": saved_secret,
                    "BOT_CHANNEL_TOKEN": saved_line_token,
                    "BOT_MODEL": line_model,
                    "BOT_SYSTEM": line_system,
                    "BOT_PORT": str(line_port),
                    "BOT_ALLOWED_USERS": line_allowed,
                    "PYTHONUNBUFFERED": "1",
                },
            )
            if res["ok"]:
                st.success(res["msg"])
            else:
                st.error(res["msg"])
            st.rerun()
    with s2:
        if st.button(
            "⏹️ 停止 Bot",
            key="line-stop",
            use_container_width=True,
            disabled=not line_status["running"],
        ):
            res = bot_runner.stop("line")
            st.info(res["msg"])
            st.rerun()
    with s3:
        if line_status["running"]:
            st.success(f"🟢 執行中（PID {line_status['pid']}，port {line_port}）")
        else:
            st.info("🔴 未執行")

    if line_status["running"]:
        st.markdown("##### 🌐 別忘了開 Cloudflare Tunnel")
        st.code(f"cloudflared tunnel --url http://localhost:{line_port}", language="bash")
        st.caption(
            "↑ 在另一個終端機跑這行，把它給的 `https://xxx.trycloudflare.com` + `/webhook` "
            "貼到 LINE Developers → Messaging API → Webhook URL"
        )

    with st.expander("📜 即時 log（最近 40 行）", expanded=line_status["running"]):
        log_text = bot_runner.tail_log("line", 40) or "(尚無 log)"
        st.code(log_text, language="text")
        log_c1, log_c2 = st.columns([1, 5])
        with log_c1:
            if st.button("🔄 重新讀取", key="line-refresh-log"):
                st.rerun()
        with log_c2:
            if st.button("🧹 清空 log", key="line-clear-log"):
                bot_runner.clear_log("line")
                st.rerun()

    with st.expander("🆘 故障排除", expanded=False):
        st.markdown(
            """
            **LINE Developers 後台按「Verify」失敗？**
            → 1) Bot 還沒啟動；
            　 2) Cloudflare Tunnel 沒開或網址打錯；
            　 3) Webhook URL 結尾忘了加 `/webhook`。

            **使用者傳訊息沒回應，但 Verify 成功？**
            → 看 log：有沒有「⛔ 簽章驗證失敗」？→ Channel Secret 貼錯。
            → 沒有任何 log？→ Webhook URL 沒設好、或 Auto-reply 沒關掉（會被它截走）。

            **Tunnel 網址每次重啟都會變？**
            → 是的，免費 trycloudflare 是臨時網址。每次重開 tunnel 後要回 LINE Developers
            　 更新 Webhook URL。想要固定網址要付費版 cloudflared 帳號 + 自己的域名。

            **使用者 chat 比較慢、第一句沒回應？**
            → LINE 對 webhook 要求 3 秒內回 200，我們有先回 200 再背景跑模型。
            　 但模型回應太久（>30 秒）時 LINE 可能不顯示 typing，等久一點就會收到。

            **怎麼拿到 userId 加白名單？**
            → 先讓對方傳一句話，log 裡會印出 `userId=Uxxxxxx…`（前 8 碼）。
            　 完整 ID 在 log 檔（`~/.claude/bots/line.log`）裡用 grep 找。
            """
        )

st.divider()
st.caption(
    "💡 Bot 是獨立背景程序，關掉 AI Hub / Streamlit 不會影響它。"
    "重開機後預設不會自動恢復——回到本頁手動按啟動即可。"
)
