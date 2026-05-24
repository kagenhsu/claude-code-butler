"""🤖 自動化任務 — 用 Claude Code CLI 跑每日排程或專案專屬任務。

兩種任務：
- ⏰ 每日排程：時間到自動跑（每天 / 每週 / 每 N 分鐘）— 需要 scheduler 在跑
- 📁 專案任務：綁某個專案資料夾，平常擺著、要用時手動「立即執行」

所有任務都走 `claude -p <prompt>`，輸出存 ~/.claude/aihub_tasks/<id>/。
"""
from __future__ import annotations

import os
import shutil
from datetime import datetime
from pathlib import Path

import streamlit as st

from lib import bot_runner, task_runner, task_store

st.set_page_config(page_title="自動化任務 | Claude Code 管家", page_icon="🤖", layout="wide")

from lib.ui import inject_style  # noqa: E402
from lib.nav import render_nav  # noqa: E402

inject_style(st)
render_nav()

st.title("🤖 自動化任務")
st.caption("讓 Claude Code 幫你定期做事、或針對某個專案一鍵跑流程")

# ── 前置檢查：claude CLI ─────────────────────────────────
_claude = shutil.which("claude")
if not _claude:
    st.error(
        "❌ 找不到 `claude` 指令 — 任務全部都靠它跑。"
        "請先安裝 [Claude Code CLI](https://docs.anthropic.com/en/docs/claude-code)，"
        "然後重新整理這頁。"
    )
    st.stop()
st.caption(f"✅ 偵測到 Claude Code CLI：`{_claude}`")

# ── 為什麼用這頁 ─────────────────────────────────────────
with st.expander("💡 這頁能幫你做什麼？", expanded=False):
    st.markdown(
        """
        ### 兩種典型用法

        **⏰ 每日排程任務** — 設一次、長期幫你跑
        - 每天 09:00 整理昨天的 git log + 寄到 Telegram
        - 每週一 08:00 自動生成週報
        - 每 30 分鐘檢查工作目錄有沒有新 PR

        **📁 專案任務** — 綁某個資料夾，需要時一鍵跑
        - 對 [~/work/proj-a](file:///Users/xujiayuan/work/proj-a) 跑「全專案程式碼審查」
        - 對 [~/blog](file:///Users/xujiayuan/blog) 跑「找出沒寫完的 TODO」
        - 對 [~/Downloads/csv](file:///Users/xujiayuan/Downloads/csv) 跑「整理這些 CSV 並生成統計報告」

        ### 任務怎麼跑？
        AI Hub 會在背景執行 `claude -p "你寫的 prompt"`，工作目錄切到你指定的路徑。
        Claude Code 有完整的工具權限（讀檔、改檔、跑指令），所以**寫 prompt 時要小心**，
        不要叫它做你還沒準備好讓它做的事（例如 `git push`）。
        """
    )

# ╔═════════════════════════════════════════════════════════╗
# ║ Scheduler 控制                                          ║
# ╚═════════════════════════════════════════════════════════╝
sched_status = bot_runner.status("scheduler")
with st.container(border=True):
    st.markdown("#### ⚙️ 排程器（Scheduler）")
    c1, c2, c3, c4 = st.columns([2, 1, 1, 2])
    with c1:
        if sched_status["running"]:
            st.success(f"🟢 執行中（PID {sched_status['pid']}）— 每 30 秒檢查一次")
        else:
            st.info("🔴 未執行 — 每日排程任務不會自動觸發")
    with c2:
        if st.button(
            "▶️ 啟動",
            key="sched-start",
            type="primary",
            use_container_width=True,
            disabled=sched_status["running"],
        ):
            res = bot_runner.start(
                "scheduler",
                [bot_runner.python_executable(), "-m", "bots.scheduler"],
                env={"PYTHONUNBUFFERED": "1"},
            )
            (st.success if res["ok"] else st.error)(res["msg"])
            st.rerun()
    with c3:
        if st.button(
            "⏹️ 停止",
            key="sched-stop",
            use_container_width=True,
            disabled=not sched_status["running"],
        ):
            res = bot_runner.stop("scheduler")
            st.info(res["msg"])
            st.rerun()
    with c4:
        st.caption(
            "Scheduler 是獨立背景程序；關掉 AI Hub 不影響它，"
            "但開機後不會自動恢復。"
        )

    with st.expander("📜 Scheduler log（最近 30 行）", expanded=False):
        log_text = bot_runner.tail_log("scheduler", 30) or "(尚無 log)"
        st.code(log_text, language="text")
        if st.button("🔄 重新讀取 log", key="sched-refresh"):
            st.rerun()

st.divider()

tab_daily, tab_proj, tab_hist = st.tabs(["⏰ 每日排程", "📁 專案任務", "📜 歷史紀錄"])

# ╔═════════════════════════════════════════════════════════╗
# ║ Tab 1: 每日排程                                          ║
# ╚═════════════════════════════════════════════════════════╝
WEEKDAYS = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]


def _render_task_card(task: dict, *, show_schedule: bool):
    is_running = task_runner.is_running(task["id"])
    with st.container(border=True):
        head1, head2 = st.columns([4, 1])
        with head1:
            status_icon = "🟢" if task.get("enabled") else "⏸️"
            st.markdown(f"### {status_icon} {task['name']}")
            meta = []
            if show_schedule:
                meta.append(f"⏰ {task_store.describe_schedule(task['schedule'])}")
            if task.get("cwd"):
                meta.append(f"📂 `{task['cwd']}`")
            if task.get("last_run_at"):
                emoji = {"success": "✅", "fail": "❌", "running": "🔄"}.get(task["last_status"], "⏺")
                meta.append(f"上次：{emoji} {task['last_run_at']}（{task.get('last_duration_sec', 0)}s）")
            else:
                meta.append("尚未執行過")
            st.caption(" · ".join(meta))
        with head2:
            if is_running:
                st.warning("🔄 執行中", icon="🔄")
            else:
                st.empty()

        with st.expander("📄 prompt 內容", expanded=False):
            st.code(task["prompt"] or "(空)", language="markdown")

        bcols = st.columns(5)
        with bcols[0]:
            if st.button(
                "▶️ 立即執行",
                key=f"run-{task['id']}",
                use_container_width=True,
                disabled=is_running,
            ):
                res = task_runner.spawn(task)
                (st.success if res["ok"] else st.warning)(res["msg"])
                st.rerun()
        with bcols[1]:
            label = "⏸️ 停用" if task.get("enabled") else "✅ 啟用"
            if st.button(label, key=f"toggle-{task['id']}", use_container_width=True):
                task_store.set_enabled(task["id"], not task.get("enabled"))
                st.rerun()
        with bcols[2]:
            if st.button("✏️ 編輯", key=f"edit-{task['id']}", use_container_width=True):
                st.session_state[f"editing-{task['id']}"] = True
                st.rerun()
        with bcols[3]:
            if st.button("📜 看 log", key=f"log-{task['id']}", use_container_width=True):
                st.session_state[f"viewing-log-{task['id']}"] = True
                st.rerun()
        with bcols[4]:
            if st.button("🗑️ 刪除", key=f"del-{task['id']}", use_container_width=True):
                st.session_state[f"confirm-del-{task['id']}"] = True
                st.rerun()

        if st.session_state.get(f"confirm-del-{task['id']}"):
            st.warning(f"確定要刪除「{task['name']}」？這會同時刪掉它的歷史紀錄索引（log 檔案保留）。")
            cc1, cc2, _ = st.columns([1, 1, 4])
            with cc1:
                if st.button("🗑️ 確認刪除", key=f"confirm-yes-{task['id']}", type="primary"):
                    task_store.delete_task(task["id"])
                    st.session_state.pop(f"confirm-del-{task['id']}", None)
                    st.rerun()
            with cc2:
                if st.button("取消", key=f"confirm-no-{task['id']}"):
                    st.session_state.pop(f"confirm-del-{task['id']}", None)
                    st.rerun()

        if st.session_state.get(f"viewing-log-{task['id']}"):
            log_p = task_runner.last_log_path(task["id"])
            if log_p:
                st.markdown(f"**最近一次 log：** `{log_p}`")
                st.code(task_runner.read_log(log_p, tail_lines=200), language="text")
            else:
                st.info("尚未有任何執行紀錄")
            if st.button("收起 log", key=f"hide-log-{task['id']}"):
                st.session_state.pop(f"viewing-log-{task['id']}", None)
                st.rerun()

        if st.session_state.get(f"editing-{task['id']}"):
            _render_edit_form(task)


def _render_edit_form(task: dict):
    st.markdown("---")
    st.markdown("##### ✏️ 編輯任務")
    with st.form(key=f"edit-form-{task['id']}", clear_on_submit=False):
        new_name = st.text_input("名稱", value=task["name"])
        new_cwd = st.text_input(
            "工作目錄（絕對路徑；專案任務必填，每日排程可留空）",
            value=task.get("cwd", ""),
            placeholder="/Users/xujiayuan/work/my-project",
        )
        new_prompt = st.text_area(
            "Prompt（餵給 `claude -p` 的內容）",
            value=task.get("prompt", ""),
            height=180,
        )

        if task["kind"] == "daily":
            sched = task.get("schedule") or {}
            mode_map = {
                "daily": "每天某時刻",
                "weekly": "每週某天某時刻",
                "interval": "每 N 分鐘",
            }
            mode_keys = list(mode_map.keys())
            current_mode = sched.get("mode") if sched.get("mode") in mode_map else "daily"
            new_mode = st.selectbox(
                "排程模式",
                mode_keys,
                index=mode_keys.index(current_mode),
                format_func=lambda k: mode_map[k],
            )
            new_schedule: dict = {"mode": new_mode}
            if new_mode in ("daily", "weekly"):
                new_time = st.text_input(
                    "時間（HH:MM，24 小時制）",
                    value=sched.get("time", "09:00"),
                    placeholder="例：09:00",
                )
                new_schedule["time"] = new_time
            if new_mode == "weekly":
                wd_idx = int(sched.get("weekday", 0)) % 7
                new_wd = st.selectbox(
                    "星期幾",
                    list(range(7)),
                    index=wd_idx,
                    format_func=lambda i: WEEKDAYS[i],
                )
                new_schedule["weekday"] = new_wd
            if new_mode == "interval":
                new_minutes = st.number_input(
                    "每幾分鐘跑一次",
                    min_value=1,
                    max_value=24 * 60,
                    value=int(sched.get("minutes", 30) or 30),
                    step=1,
                )
                new_schedule["minutes"] = int(new_minutes)
        else:
            new_schedule = {}

        c1, c2 = st.columns([1, 1])
        with c1:
            saved = st.form_submit_button("💾 儲存", type="primary", use_container_width=True)
        with c2:
            cancelled = st.form_submit_button("取消", use_container_width=True)

        if saved:
            task_store.update_task(
                task["id"],
                name=new_name.strip(),
                cwd=new_cwd.strip(),
                prompt=new_prompt,
                schedule=new_schedule,
            )
            st.session_state.pop(f"editing-{task['id']}", None)
            st.rerun()
        if cancelled:
            st.session_state.pop(f"editing-{task['id']}", None)
            st.rerun()


def _render_new_form(kind: str, container):
    """kind: daily / project"""
    key_prefix = f"new-{kind}"
    if not st.session_state.get(f"show-{key_prefix}"):
        if container.button(
            "➕ 新增" + ("每日任務" if kind == "daily" else "專案任務"),
            key=f"open-{key_prefix}",
            type="primary",
        ):
            st.session_state[f"show-{key_prefix}"] = True
            st.rerun()
        return

    with container.form(key=f"form-{key_prefix}", clear_on_submit=False):
        st.markdown(f"##### ➕ 新增{'每日' if kind == 'daily' else '專案'}任務")
        name = st.text_input(
            "名稱",
            placeholder="例：每日 git log 摘要" if kind == "daily" else "例：Pro Link 程式碼審查",
            key=f"{key_prefix}-name",
        )
        cwd = st.text_input(
            "工作目錄（絕對路徑）" + ("" if kind == "project" else "，留空 = home"),
            placeholder="/Users/xujiayuan/work/my-project",
            key=f"{key_prefix}-cwd",
        )
        prompt = st.text_area(
            "Prompt（餵給 `claude -p`）",
            placeholder=(
                "整理今天的 git log，把每個 commit 的 why 寫成一句中文，最後輸出 markdown 摘要。"
                if kind == "daily"
                else "對這個專案跑完整程式碼審查，列出 5 個最重要的問題與建議修法。"
            ),
            height=180,
            key=f"{key_prefix}-prompt",
        )

        schedule: dict = {}
        if kind == "daily":
            mode_map = {
                "daily": "每天某時刻",
                "weekly": "每週某天某時刻",
                "interval": "每 N 分鐘",
            }
            mode_keys = list(mode_map.keys())
            mode = st.selectbox(
                "排程模式", mode_keys, format_func=lambda k: mode_map[k], key=f"{key_prefix}-mode"
            )
            schedule["mode"] = mode
            if mode in ("daily", "weekly"):
                schedule["time"] = st.text_input(
                    "時間（HH:MM）", value="09:00", key=f"{key_prefix}-time"
                )
            if mode == "weekly":
                schedule["weekday"] = st.selectbox(
                    "星期幾",
                    list(range(7)),
                    format_func=lambda i: WEEKDAYS[i],
                    key=f"{key_prefix}-wd",
                )
            if mode == "interval":
                schedule["minutes"] = int(
                    st.number_input(
                        "每幾分鐘跑一次", min_value=1, max_value=24 * 60, value=30,
                        step=1, key=f"{key_prefix}-minutes",
                    )
                )

        c1, c2 = st.columns([1, 1])
        with c1:
            saved = st.form_submit_button("💾 建立", type="primary", use_container_width=True)
        with c2:
            cancelled = st.form_submit_button("取消", use_container_width=True)

        if saved:
            if not name.strip() or not prompt.strip():
                st.error("名稱與 Prompt 都要填")
            elif kind == "project" and not cwd.strip():
                st.error("專案任務一定要指定工作目錄")
            else:
                task_store.create_task(
                    name=name, kind=kind, prompt=prompt, cwd=cwd.strip(),
                    schedule=schedule, enabled=True,
                )
                st.session_state[f"show-{key_prefix}"] = False
                st.success("✅ 已建立")
                st.rerun()
        if cancelled:
            st.session_state[f"show-{key_prefix}"] = False
            st.rerun()


# ── Tab 1：每日 ──────────────────────────────────────────
with tab_daily:
    st.markdown("時間到自動觸發 — 需要上面的 Scheduler 在跑。")
    if not sched_status["running"]:
        st.warning("⚠️ Scheduler 目前沒在跑，下面的任務不會自動觸發。手動「立即執行」仍可用。")

    _render_new_form("daily", st.container())

    daily_tasks = task_store.list_tasks(kind="daily")
    if not daily_tasks:
        st.info("還沒有每日任務 — 點上面「➕ 新增每日任務」開始。")
    else:
        for t in daily_tasks:
            _render_task_card(t, show_schedule=True)

# ── Tab 2：專案 ──────────────────────────────────────────
with tab_proj:
    st.markdown("綁某個資料夾，平常擺著、需要時手動「立即執行」。")

    _render_new_form("project", st.container())

    project_tasks = task_store.list_tasks(kind="project")
    if not project_tasks:
        st.info("還沒有專案任務 — 點上面「➕ 新增專案任務」開始。")
    else:
        # 按 cwd 分組
        groups: dict[str, list[dict]] = {}
        for t in project_tasks:
            groups.setdefault(t.get("cwd") or "(未設定)", []).append(t)
        for cwd, items in groups.items():
            st.markdown(f"#### 📂 `{cwd}`")
            for t in items:
                _render_task_card(t, show_schedule=False)

# ── Tab 3：歷史 ──────────────────────────────────────────
with tab_hist:
    history = task_store.list_history(limit=100)
    h1, h2 = st.columns([5, 1])
    with h1:
        st.markdown(f"最近 **{len(history)}** 筆執行紀錄")
    with h2:
        if st.button("🧹 清空", key="clear-hist", disabled=not history):
            task_store.clear_history()
            st.rerun()

    if not history:
        st.info("還沒有任何執行紀錄")
    else:
        for h in history:
            emoji = {"success": "✅", "fail": "❌", "running": "🔄"}.get(h["status"], "⏺")
            with st.container(border=True):
                cc1, cc2, cc3 = st.columns([3, 2, 1])
                with cc1:
                    st.markdown(f"**{emoji} {h.get('name') or '(未命名)'}**")
                    st.caption(f"開始 {h['started_at']} · 結束 {h['ended_at']} · {h.get('duration_sec', 0)}s")
                with cc2:
                    st.caption(f"`{h.get('log_path', '')}`")
                with cc3:
                    if st.button("📜 看 log", key=f"hist-view-{h.get('started_at')}-{h.get('task_id','')}"):
                        st.session_state["view-hist-log"] = h.get("log_path")
                        st.rerun()

        if st.session_state.get("view-hist-log"):
            p = st.session_state["view-hist-log"]
            st.markdown(f"#### 📜 `{p}`")
            st.code(task_runner.read_log(p, tail_lines=400), language="text")
            if st.button("收起", key="hide-hist-log"):
                st.session_state.pop("view-hist-log", None)
                st.rerun()
