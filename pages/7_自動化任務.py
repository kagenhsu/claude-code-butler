"""🤖 自動化任務 & Agent 監控 — 占位頁（v1）

看現在有哪些 AI 代理人在執行、什麼自動化任務排在那裡、做完了什麼
"""
from datetime import datetime, timedelta

import streamlit as st

st.set_page_config(page_title="自動化任務 | AI Hub", page_icon="🤖", layout="wide")
st.title("🤖 自動化任務 & Agent 監控")
st.caption("看你的 AI 代理人在做什麼、管理排程任務、查看歷史紀錄")

# ── 頁面說明 ──────────────────────────────────────────────
with st.expander("❓ 這個頁面是做什麼的？", expanded=False):
    st.markdown(
        """
        ### 兩種「自動跑」的東西
        | 類型 | 例子 | 觸發方式 |
        |------|------|---------|
        | **排程任務** | 「每天早上 9 點檢查 CI 狀態」 | 時間到了自動跑 |
        | **AI 代理人** | 「在背景找 bug 並回報」 | 手動或被觸發後一直跑 |

        這個頁面 v2 開始會：
        - 看現在哪個 agent 在跑、卡在哪一步
        - 排程新的任務（不用打 cron 語法）
        - 看歷史成敗與輸出
        - 一鍵停止 / 重跑

        ### 整合計畫
        - **Claude Code `/loop`** — 重複跑某個 prompt
        - **Claude Code `/schedule`** — 排程遠端 agent
        - **系統 cron / launchd** — 真正的作業系統排程
        - **背景 Python script** — 你自己寫的小程式
        """
    )

st.info("🚧 **v1 為占位頁面**。下面是規劃中的 UI 預覽，方便你想像未來長什麼樣。")

# ── 分頁 ──────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["🔴 執行中", "⏰ 排程任務", "📜 歷史紀錄"])

# ─── Tab 1：執行中的 agent ────────────────────────────────
with tab1:
    st.subheader("🔴 目前執行中的 Agent")
    st.caption("即時看到每個代理人在做什麼。v2 會自動每幾秒更新一次。")

    # 模擬資料
    running_agents = [
        {
            "id": "agent-001",
            "name": "Pro Link 程式碼審查",
            "started": datetime.now() - timedelta(minutes=3),
            "current_step": "正在分析 customer.php 第 45-78 行",
            "progress": 60,
            "type": "subagent",
        },
        {
            "id": "agent-002",
            "name": "今日工作摘要",
            "started": datetime.now() - timedelta(seconds=20),
            "current_step": "讀取今日 git log",
            "progress": 15,
            "type": "loop",
        },
    ]

    for agent in running_agents:
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            with c1:
                st.markdown(f"### 🟢 {agent['name']}")
                st.caption(f"ID: `{agent['id']}` · 類型: `{agent['type']}` · 已執行 {(datetime.now() - agent['started']).seconds} 秒")
                st.write(f"**目前步驟**：{agent['current_step']}")
                st.progress(agent["progress"] / 100, text=f"{agent['progress']}%")
            with c2:
                st.button("查看輸出", key=f"view-{agent['id']}", disabled=True, use_container_width=True)
                st.button("⏸️ 暫停", key=f"pause-{agent['id']}", disabled=True, use_container_width=True)
                st.button("⏹️ 停止", key=f"stop-{agent['id']}", disabled=True, use_container_width=True)

# ─── Tab 2：排程任務 ──────────────────────────────────────
with tab2:
    st.subheader("⏰ 排程任務")
    st.caption("時間到自動觸發。v2 提供圖形化排程，不用打 cron 語法。")

    cl, cr = st.columns([5, 1])
    with cr:
        st.button("➕ 新增排程", disabled=True, use_container_width=True)

    scheduled = [
        {"name": "每日 09:00 看 CI 狀態", "next_run": "明天 09:00", "type": "cron", "enabled": True},
        {"name": "每 15 分鐘檢查新 PR", "next_run": "12 分鐘後", "type": "interval", "enabled": True},
        {"name": "每週一寄週報", "next_run": "下週一 08:00", "type": "cron", "enabled": False},
    ]
    for s in scheduled:
        with st.container(border=True):
            c1, c2, c3 = st.columns([4, 2, 1])
            with c1:
                emoji = "✅" if s["enabled"] else "⏸️"
                st.markdown(f"### {emoji} {s['name']}")
                st.caption(f"類型: `{s['type']}`")
            with c2:
                st.markdown(f"**下次執行**\n\n{s['next_run']}")
            with c3:
                st.button("編輯", key=f"sch-edit-{s['name']}", disabled=True, use_container_width=True)
                st.button("立即跑", key=f"sch-run-{s['name']}", disabled=True, use_container_width=True)

# ─── Tab 3：歷史 ──────────────────────────────────────────
with tab3:
    st.subheader("📜 歷史執行紀錄")
    st.caption("最近 100 筆執行結果。v2 提供搜尋、篩選、匯出。")

    history = [
        {"time": "10:42", "name": "程式碼審查", "status": "✅ 成功", "duration": "1m 23s"},
        {"time": "10:30", "name": "今日工作摘要", "status": "✅ 成功", "duration": "12s"},
        {"time": "09:00", "name": "CI 狀態檢查", "status": "⚠️ 警告（2 failures）", "duration": "8s"},
        {"time": "08:15", "name": "Telegram Bot 啟動", "status": "❌ 失敗（token 過期）", "duration": "2s"},
        {"time": "昨天 23:11", "name": "備份 skills", "status": "✅ 成功", "duration": "3s"},
    ]
    st.table(history)
