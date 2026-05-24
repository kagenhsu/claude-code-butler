"""🪝 Hooks — 管理 Claude Code 的事件鉤子。

Hooks 是 Claude Code 的「觸發即執行」機制：在工具呼叫前後、session 啟動、
assistant 結束回合等事件發生時，自動跑一段 shell 指令。

兩個範圍：
- 🌐 全域：~/.claude/settings.json（所有 Claude Code session 都吃）
- 📁 專案：<project>/.claude/settings.json（只在那個專案資料夾啟動的 session 吃）

頁面結構：
- 上方範圍切換（全域 / 專案）
- 三個 tab：📋 目前的 hooks ／ ➕ 新增 ／ 📦 範本
- 每條 hook 都能「測試一下」— 直接 bash 跑一次，看 exit code、stdout、stderr
"""
from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from lib import hooks_store

st.set_page_config(page_title="Hooks | Claude Code 管家", page_icon="🪝", layout="wide")

from lib.ui import inject_style  # noqa: E402
from lib.nav import render_nav  # noqa: E402

inject_style(st)
render_nav()

st.title("🪝 Hooks")
st.caption("管理 Claude Code 的事件鉤子 — 觸發即執行的 shell 指令，可以擋工具呼叫、自動 format、發通知")

# ── 教學 ───────────────────────────────────────────────
with st.container(border=True):
    st.markdown(
        """
        ### 🤔 什麼是 Hooks？

        想像你跟 Claude Code 共用同一個工作環境。它要動手做事的時候（跑指令、改檔），
        你想插一段「自動檢查 / 自動跟著做」的動作。例如：

        - 🛡️ Claude 想跑 `rm -rf /` → **直接擋下來**（PreToolUse + matcher=Bash）
        - 🎨 Claude 改完 .py → **自動跑 ruff format**（PostToolUse + matcher=Write）
        - 🔔 Claude 跑完一個長任務 → **桌面跳通知讓你回來看**（Stop）
        - 📜 每一條 Bash 指令 → **寫進稽核 log**（PreToolUse + matcher=Bash）

        Hook 是一段 shell 指令；事件發生時，Claude Code 用 stdin 餵 JSON 上下文進去。
        你的指令可以 `jq` 讀 stdin、決定要不要 `exit 2` 阻止這次呼叫。
        """
    )

with st.expander("📖 所有事件一覽（matcher 用法）", expanded=False):
    for ev in hooks_store.EVENTS:
        wants_matcher = ev in hooks_store.MATCHER_EVENTS
        suffix = "（要設 matcher：工具名稱，例如 `Bash` 或 `Write|Edit`）" if wants_matcher else "（不需要 matcher）"
        st.markdown(f"- **`{ev}`** {suffix}\n  → {hooks_store.EVENT_DESC[ev]}")
    st.caption(
        "💡 完整文件：[Claude Code Hooks](https://docs.anthropic.com/en/docs/claude-code/hooks)"
    )


# ╔═════════════════════════════════════════════════════════╗
# ║ 範圍選擇                                                ║
# ╚═════════════════════════════════════════════════════════╝
st.markdown("### 📂 套用範圍")

scope_col1, scope_col2 = st.columns([1, 3])
with scope_col1:
    scope = st.radio(
        "範圍",
        ["🌐 全域", "📁 專案"],
        index=0,
        key="hooks-scope",
        label_visibility="collapsed",
    )

settings_path: Path
project_dir = ""

if scope == "🌐 全域":
    settings_path = hooks_store.global_settings_file()
    with scope_col2:
        st.info(f"使用全域設定：`{settings_path}`")
else:
    candidates = hooks_store.find_candidate_projects()
    options = ["（手動輸入路徑）"] + [str(p) for p in candidates]
    with scope_col2:
        sel = st.selectbox("選一個專案資料夾", options, key="hooks-proj-select")
        if sel == "（手動輸入路徑）":
            project_dir = st.text_input(
                "輸入專案絕對路徑",
                placeholder="/Users/xujiayuan/work/my-project",
                key="hooks-proj-path",
            )
        else:
            project_dir = sel
    if not project_dir or not Path(project_dir).is_dir():
        st.warning("請選一個存在的專案資料夾")
        st.stop()
    settings_path = hooks_store.project_settings_file(project_dir)
    st.info(f"使用專案設定：`{settings_path}`")
    if not settings_path.is_file():
        st.caption("（這個檔案還不存在，第一次新增 hook 時會自動建立）")

# 載入該範圍的 hooks
flat = hooks_store.list_flat_entries(settings_path)

# 統計
ev_counts: dict[str, int] = {}
for entry in flat:
    ev_counts[entry["event"]] = ev_counts.get(entry["event"], 0) + 1

scope_label = "全域" if scope == "🌐 全域" else f"專案 `{project_dir}`"
if flat:
    summary = "、".join(f"{e}×{n}" for e, n in ev_counts.items())
    st.success(f"✅ 目前 {scope_label} 共有 **{len(flat)}** 個 hook（{summary}）")
else:
    st.info(f"📭 {scope_label} 還沒設定任何 hook")

st.divider()

tab_list, tab_add, tab_tmpl = st.tabs(["📋 目前的 hooks", "➕ 新增", "📦 範本"])


# ╔═════════════════════════════════════════════════════════╗
# ║ Tab: 列表                                               ║
# ╚═════════════════════════════════════════════════════════╝
def _render_test_block(command: str, cwd: str = "", *, key_prefix: str):
    """『測試一下』區塊：跑一次指令、顯示結果"""
    if st.button("🧪 測試一下（bash -c）", key=f"test-{key_prefix}"):
        st.session_state[f"test-result-{key_prefix}"] = hooks_store.dry_run(command, cwd=cwd)
    result = st.session_state.get(f"test-result-{key_prefix}")
    if result:
        rc = result["rc"]
        emoji = "✅" if rc == 0 else ("⛔" if rc == 2 else "❌")
        st.markdown(f"**{emoji} exit code = {rc} · {result['duration_ms']} ms**")
        if rc == 2:
            st.caption("（exit 2 在 PreToolUse 是『阻止這次工具呼叫』的意思）")
        if result["stdout"]:
            st.text("stdout:")
            st.code(result["stdout"], language="text")
        if result["stderr"]:
            st.text("stderr:")
            st.code(result["stderr"], language="text")


with tab_list:
    if not flat:
        st.info("沒有任何 hook，到「➕ 新增」或「📦 範本」加一個。")
    else:
        # 依事件分組顯示
        by_event: dict[str, list[dict]] = {}
        for e in flat:
            by_event.setdefault(e["event"], []).append(e)

        for ev in hooks_store.EVENTS:
            if ev not in by_event:
                continue
            st.markdown(f"#### `{ev}`  · {hooks_store.EVENT_DESC[ev]}")
            for entry in by_event[ev]:
                key_prefix = entry["uid"]
                with st.container(border=True):
                    h1, h2 = st.columns([4, 1])
                    with h1:
                        if ev in hooks_store.MATCHER_EVENTS:
                            st.markdown(f"**matcher**: `{entry['matcher'] or '(全部工具)'}`")
                        st.code(entry["command"], language="bash")
                        if entry.get("timeout"):
                            st.caption(f"timeout：{entry['timeout']} 秒")
                    with h2:
                        edit_key = f"edit-{key_prefix}"
                        if st.button("✏️ 編輯", key=f"btn-edit-{key_prefix}", use_container_width=True):
                            st.session_state[edit_key] = True
                            st.rerun()
                        if st.button("🗑️ 刪除", key=f"btn-del-{key_prefix}", use_container_width=True):
                            st.session_state[f"confirm-{key_prefix}"] = True
                            st.rerun()

                    if st.session_state.get(f"confirm-{key_prefix}"):
                        st.warning("確定要刪掉這個 hook？")
                        c1, c2, _ = st.columns([1, 1, 4])
                        with c1:
                            if st.button("🗑️ 確認", key=f"yes-{key_prefix}", type="primary"):
                                hooks_store.delete_hook(
                                    settings_path,
                                    event=entry["event"],
                                    group_idx=entry["group_idx"],
                                    hook_idx=entry["hook_idx"],
                                )
                                st.session_state.pop(f"confirm-{key_prefix}", None)
                                st.rerun()
                        with c2:
                            if st.button("取消", key=f"no-{key_prefix}"):
                                st.session_state.pop(f"confirm-{key_prefix}", None)
                                st.rerun()

                    if st.session_state.get(edit_key):
                        with st.form(key=f"form-{key_prefix}"):
                            st.markdown("**編輯這個 hook**")
                            new_matcher = ""
                            if ev in hooks_store.MATCHER_EVENTS:
                                new_matcher = st.text_input(
                                    "matcher（工具名稱，可用 `|` 串接，留空 = 全部）",
                                    value=entry["matcher"],
                                )
                            new_cmd = st.text_area(
                                "指令（會被 `bash -c` 執行）",
                                value=entry["command"],
                                height=140,
                            )
                            new_to = st.number_input(
                                "timeout（秒，0 = 不設）",
                                min_value=0,
                                max_value=600,
                                value=int(entry.get("timeout") or 0),
                            )
                            fc1, fc2 = st.columns(2)
                            with fc1:
                                save = st.form_submit_button("💾 儲存", type="primary", use_container_width=True)
                            with fc2:
                                cancel = st.form_submit_button("取消", use_container_width=True)
                            if save:
                                ok, msg = hooks_store.validate_command(new_cmd)
                                if not ok:
                                    st.error(f"❌ syntax 有問題：{msg}")
                                else:
                                    hooks_store.update_hook(
                                        settings_path,
                                        event=entry["event"],
                                        group_idx=entry["group_idx"],
                                        hook_idx=entry["hook_idx"],
                                        matcher=new_matcher,
                                        command=new_cmd,
                                        timeout=int(new_to) or None,
                                    )
                                    st.session_state.pop(edit_key, None)
                                    st.rerun()
                            if cancel:
                                st.session_state.pop(edit_key, None)
                                st.rerun()

                    _render_test_block(entry["command"], cwd=project_dir, key_prefix=key_prefix)

# ╔═════════════════════════════════════════════════════════╗
# ║ Tab: 新增                                                ║
# ╚═════════════════════════════════════════════════════════╝
with tab_add:
    st.markdown("從零寫一個 hook：")
    with st.form("add-hook-form"):
        a_event = st.selectbox(
            "事件",
            hooks_store.EVENTS,
            format_func=lambda e: f"{e}  — {hooks_store.EVENT_DESC[e][:40]}…",
        )
        a_matcher = ""
        if a_event in hooks_store.MATCHER_EVENTS:
            a_matcher = st.text_input(
                "matcher（工具名稱，可用 `|` 串接；留空 = 全部工具）",
                placeholder="例：Bash 或 Write|Edit|MultiEdit",
            )
        else:
            st.caption(f"`{a_event}` 不需要 matcher")
        a_cmd = st.text_area(
            "指令（會被 `bash -c` 執行；stdin 是 JSON 上下文）",
            height=180,
            placeholder=(
                'echo "[$(date)] $(jq -r .tool_input.command)" >> ~/.claude/audit.log\n'
                "# 或：\n"
                "# cmd=$(jq -r .tool_input.command)\n"
                "# echo \"$cmd\" | grep -q dangerous && { echo blocked >&2; exit 2; }"
            ),
        )
        a_to = st.number_input(
            "timeout（秒，0 = 不設）",
            min_value=0,
            max_value=600,
            value=0,
            help="hook 跑太久時強制中斷。PreToolUse 建議短一點（< 5s），不然 Claude 會卡住等",
        )
        cval, csub = st.columns([1, 1])
        with cval:
            check = st.form_submit_button("🔍 只 syntax check", use_container_width=True)
        with csub:
            submit = st.form_submit_button("💾 加入", type="primary", use_container_width=True)

        if check:
            ok, msg = hooks_store.validate_command(a_cmd)
            (st.success if ok else st.error)(msg)
        if submit:
            ok, msg = hooks_store.validate_command(a_cmd)
            if not ok:
                st.error(f"❌ syntax 有問題：{msg}")
            else:
                hooks_store.add_hook(
                    settings_path,
                    event=a_event,
                    matcher=a_matcher,
                    command=a_cmd,
                    timeout=int(a_to) or None,
                )
                st.success(f"✅ 已加入 `{a_event}` hook")
                st.rerun()


# ╔═════════════════════════════════════════════════════════╗
# ║ Tab: 範本                                                ║
# ╚═════════════════════════════════════════════════════════╝
with tab_tmpl:
    st.markdown("一鍵套用常見場景：")
    for tpl in hooks_store.TEMPLATES:
        with st.container(border=True):
            t1, t2 = st.columns([4, 1])
            with t1:
                st.markdown(f"### {tpl['name']}")
                st.caption(tpl["desc"])
                meta = f"`{tpl['event']}`"
                if tpl.get("matcher"):
                    meta += f"  · matcher = `{tpl['matcher']}`"
                st.markdown(meta)
                st.code(tpl["command"], language="bash")
            with t2:
                if st.button(
                    "➕ 套用到此範圍",
                    key=f"apply-{tpl['id']}",
                    type="primary",
                    use_container_width=True,
                ):
                    hooks_store.add_hook(
                        settings_path,
                        event=tpl["event"],
                        matcher=tpl.get("matcher", ""),
                        command=tpl["command"],
                    )
                    st.success(f"✅ 已套用「{tpl['name']}」到 {scope_label}")
                    st.rerun()

st.divider()

# ── 故障排除 ─────────────────────────────────────────────
with st.expander("🆘 故障排除 / 常見問題", expanded=False):
    st.markdown(
        """
        **Hook 設了但好像沒生效？**
        → 重啟一次 Claude Code session（hooks 在 session 啟動時 load）。
        → 在 Claude Code 裡跑 `claude --debug` 觀察是否有 hook 觸發訊息。

        **怎麼讀 stdin 的 JSON？**
        → Bash 裡用 `jq`：`cmd=$(jq -r .tool_input.command)`、`f=$(jq -r .tool_input.file_path)`
        → 不熟 jq 可以先用 `cat > /tmp/hook-input.json` 把 stdin dump 下來研究

        **exit code 的意義**
        - `0` — 通過，不做任何事
        - `2` — **阻止這次呼叫**（PreToolUse / UserPromptSubmit 適用），stderr 會餵回 Claude
        - 其他非 0 — 警告但不阻擋

        **PreToolUse 為什麼要設 timeout？**
        → Claude 會等 hook 跑完才繼續。如果忘了結束（例如指令在等 stdin）→ 整個 session 卡住。
          建議 PreToolUse 都設 timeout（5–10 秒）。

        **改了之後在新的 session 才會吃到？**
        → 是的。settings.json 是 session 啟動時讀一次。
        """
    )

# 直接看 raw JSON
with st.expander("🔧 看 raw settings.json", expanded=False):
    if settings_path.is_file():
        try:
            raw = settings_path.read_text(encoding="utf-8")
            st.code(raw, language="json")
        except OSError as e:
            st.error(f"讀檔失敗：{e}")
    else:
        st.caption("（檔案還不存在）")
