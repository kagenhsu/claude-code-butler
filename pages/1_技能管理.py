"""📂 Skills 管理 — 列表 / 新增 / 編輯 / 刪除"""
from __future__ import annotations

import streamlit as st

from lib.skills import (
    Skill,
    delete_skill,
    list_skills,
    load_skill,
    save_skill,
    validate_name,
)
from lib.templates import SKILL_TEMPLATES, get_template

st.set_page_config(page_title="Skills | AI Hub", page_icon="📂", layout="wide")
st.title("📂 Skills 管理")

# ── 頁面說明（新手必看） ──────────────────────────────────
with st.expander("❓ 什麼是 Skill？我要怎麼用？", expanded=False):
    st.markdown(
        """
        ### 一句話解釋
        Skill 是**教 Claude Code 做某件事的腳本**，建立後可在 Claude Code 終端機輸入 `/skill 名稱` 觸發。

        ### 簡單例子
        你建立一個叫 `code-review` 的 skill，內容是「請審查我修改的程式碼…」，
        之後在 Claude Code 只要打 `/code-review`，Claude 就會照你寫的去做。

        ### 怎麼開始？
        1. 點下方「**📋 從範本建立**」其中一個 → 一鍵建好
        2. 或點「**➕ 從零開始**」自己寫
        3. 建好之後，**重啟 Claude Code**，輸入 `/<你的 skill 名稱>` 就能用

        ### 檔案存在哪？
        `~/.claude/skills/<skill 名稱>/SKILL.md`（這個面板自動幫你管，不用手動編輯）
        """
    )

st.caption(f"目前位置：`~/.claude/skills/`（使用者層，所有專案都吃得到）")


# ── Session State 初始化 ──────────────────────────────────
if "edit_target" not in st.session_state:
    st.session_state.edit_target = None
if "delete_target" not in st.session_state:
    st.session_state.delete_target = None
if "prefill" not in st.session_state:
    st.session_state.prefill = None


def _switch_to(target: str | None, prefill: dict | None = None) -> None:
    st.session_state.edit_target = target
    st.session_state.delete_target = None
    st.session_state.prefill = prefill
    st.rerun()


# ── 工具列 ──────────────────────────────────────────────
col_l, col_r1, col_r2 = st.columns([4, 1, 1])
with col_l:
    st.write("")
with col_r1:
    if st.session_state.edit_target is None:
        if st.button("📋 從範本", use_container_width=True, help="從現成範本一鍵建立 skill"):
            _switch_to("__templates__")
with col_r2:
    if st.session_state.edit_target is None:
        if st.button("➕ 從零開始", type="primary", use_container_width=True):
            _switch_to("__new__")
    else:
        if st.button("← 返回列表", use_container_width=True):
            _switch_to(None)

st.divider()


# ── 範本選擇器 ──────────────────────────────────────────
def render_templates() -> None:
    st.subheader("📋 從範本建立 Skill")
    st.info("選一個範本，按「使用此範本」會幫你預先填好內容，再按儲存就完成。")

    for tpl in SKILL_TEMPLATES:
        with st.container(border=True):
            c1, c2, c3 = st.columns([1, 5, 2])
            with c1:
                st.markdown(f"# {tpl['icon']}")
            with c2:
                st.markdown(f"### {tpl['title']}")
                st.write(tpl["description_for_user"])
                st.caption(f"建立後可用 `/{tpl['name']}` 觸發")
            with c3:
                if st.button("使用此範本", key=f"tpl-{tpl['id']}", type="primary", use_container_width=True):
                    _switch_to(
                        "__new__",
                        prefill={
                            "name": tpl["name"],
                            "description": tpl["description"],
                            "body": tpl["body"],
                        },
                    )


# ── 列表 ──────────────────────────────────────────────
def render_list() -> None:
    try:
        skills = list_skills()
    except Exception as e:
        st.error(f"讀取 skills 失敗：{e}")
        return

    if not skills:
        st.info(
            "👋 **目前還沒有任何 skill。**\n\n"
            "建議起手式：\n"
            "1. 點右上「**📋 從範本**」選一個現成的（最快，1 分鐘搞定）\n"
            "2. 或點「**➕ 從零開始**」自己寫"
        )
        st.image(
            "https://placehold.co/800x200/e0f2fe/0369a1?text=Skills+is+empty+-+click+template+to+start",
            use_container_width=True,
        )
        return

    st.caption(f"共 **{len(skills)}** 個 skill")

    for s in skills:
        with st.container(border=True):
            top_l, top_r = st.columns([5, 2])
            with top_l:
                title = f"### `/{s.folder}`"
                if s.broken:
                    title += " ⚠️"
                st.markdown(title)
                if s.description:
                    st.write(s.description)
                else:
                    st.caption("_（無描述）_")
            with top_r:
                b1, b2 = st.columns(2)
                with b1:
                    if st.button("編輯", key=f"edit-{s.folder}", use_container_width=True):
                        _switch_to(s.folder)
                with b2:
                    if st.button("刪除", key=f"del-{s.folder}", use_container_width=True):
                        st.session_state.delete_target = s.folder
                        st.rerun()

    if st.session_state.delete_target:
        target = st.session_state.delete_target
        st.divider()
        st.warning(f"⚠️ 確定要刪除 skill `{target}` 嗎？此動作無法復原。")
        c1, c2, _ = st.columns([1, 1, 4])
        with c1:
            if st.button("確認刪除", type="primary"):
                try:
                    delete_skill(target)
                    st.session_state.delete_target = None
                    st.success(f"已刪除 `{target}`")
                    st.rerun()
                except Exception as e:
                    st.error(f"刪除失敗：{e}")
        with c2:
            if st.button("取消"):
                st.session_state.delete_target = None
                st.rerun()


# ── 編輯 / 新增表單 ──────────────────────────────────────
def render_form(folder: str | None) -> None:
    is_new = folder is None or folder == "__new__"

    if is_new:
        st.subheader("➕ 新增 Skill")
        prefill = st.session_state.prefill or {}
        skill = Skill(
            folder=prefill.get("name", ""),
            name=prefill.get("name", ""),
            description=prefill.get("description", ""),
            body=prefill.get("body", "# 新 Skill\n\n在這裡描述 Claude 該怎麼執行這個任務…\n"),
        )
        # 用完就清掉預填，避免下次新增還帶著
        st.session_state.prefill = None
    else:
        st.subheader(f"✏️ 編輯 `{folder}`")
        try:
            skill = load_skill(folder)
        except Exception as e:
            st.error(f"讀取失敗：{e}")
            return

    # 教學提示
    with st.expander("💡 寫好一個 Skill 的 3 個訣竅", expanded=False):
        st.markdown(
            """
            1. **名稱要好打** — `code-review` 比 `crv` 好，未來自己也記得。
            2. **描述寫清楚做什麼** — Claude 用這句話判斷要不要呼叫這個 skill。
               例：「對 git diff 做完整程式碼審查」比「審查」清楚一萬倍。
            3. **內容用條列式** — Claude 對「步驟 1、2、3」這種格式反應最好。
            """
        )

    with st.form("skill_form", clear_on_submit=False):
        new_name = st.text_input(
            "🏷️ 名稱（也是 slash command）",
            value=skill.folder if not is_new else skill.name,
            placeholder="例如：code-review",
            help="只能用小寫英數字、底線、連字號，最多 64 字。例：`code-review`、`daily_summary`。建立後在 Claude Code 用 `/code-review` 觸發。",
        )
        new_desc = st.text_input(
            "📝 描述（Claude 用這句判斷是否呼叫）",
            value=skill.description,
            placeholder="例如：對 git diff 做完整程式碼審查",
            help="寫一句清楚的話描述這個 skill 在做什麼。要具體！不要寫『審查』而是寫『對 git diff 做完整程式碼審查』。",
        )
        new_body = st.text_area(
            "📄 內容（Markdown，這是給 Claude 看的指示）",
            value=skill.body,
            height=400,
            help="用 Markdown 寫指示給 Claude。建議用條列式：『1. 先做這個 2. 再做那個』。可以包含程式碼區塊、表格、強調等。",
        )

        c1, c2 = st.columns([1, 5])
        with c1:
            submitted = st.form_submit_button("💾 儲存", type="primary", use_container_width=True)

        if submitted:
            if not validate_name(new_name):
                st.error("❌ 名稱不合法。只能用**小寫英數字、底線、連字號**，且必須以英數字開頭。例如：`code-review`、`my_skill1`")
                return
            if not new_desc.strip():
                st.error("❌ 描述不能空白。Claude 需要這句話來決定是否呼叫這個 skill。")
                return
            try:
                save_skill(
                    name=new_name.strip(),
                    description=new_desc.strip(),
                    body=new_body,
                    old_folder=None if is_new else skill.folder,
                )
                st.success(
                    f"✅ 已儲存 `{new_name}`！\n\n"
                    f"**下一步**：重啟 Claude Code，輸入 `/{new_name}` 就能用了。"
                )
                st.session_state.edit_target = None
                st.rerun()
            except Exception as e:
                st.error(f"儲存失敗：{e}")


# ── 渲染分發 ──────────────────────────────────────────────
target = st.session_state.edit_target
if target is None:
    render_list()
elif target == "__templates__":
    render_templates()
else:
    render_form(None if target == "__new__" else target)
