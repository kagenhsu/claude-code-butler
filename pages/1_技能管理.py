"""📂 Skills 管理 — 列表 / 新增 / 編輯 / 刪除 / 從 GitHub 安裝"""
from __future__ import annotations

from pathlib import Path

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
from lib.github_skill import (
    FetchedSkill,
    SkillCollection,
    fetch as github_fetch,
    fetch_skill_from_github,
    hydrate_candidate,
)
from lib import install_skill as installer
from lib import skill_directory

st.set_page_config(page_title="技能管理 | Claude Code 管家", page_icon="📂", layout="wide")

from lib.ui import inject_style
from lib.nav import render_nav
inject_style(st)
render_nav()

st.title("📂 技能管理")

# ── 頁面說明（新手必看） ──────────────────────────────────
with st.expander("❓ 什麼是 Skill？我要怎麼用？", expanded=False):
    st.markdown(
        """
        ### 一句話解釋
        Skill 是**教 Claude Code 做某件事的腳本**，建立後可在 Claude Code 終端機輸入 `/名稱` 觸發。

        ### 簡單例子
        你建立一個叫 `code-review` 的 skill，內容是「請審查我修改的程式碼…」，
        之後在 Claude Code 只要打 `/code-review`，Claude 就會照你寫的去做。

        ### 怎麼開始？
        1. 點右上「**🌐 安裝外部 Skill**」→ 從 4 種來源裝（GitHub repo / 任意 URL / 貼內容 / 上傳 .md）
        2. 或點「**📋 從範本**」選一個現成的 → 一鍵建好
        3. 或點「**➕ 從零開始**」自己寫
        4. 建好之後，在 Claude Code 輸入 `/<你的 skill 名稱>` 就能用

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
if "github_result" not in st.session_state:
    st.session_state.github_result = None


def _switch_to(target: str | None, prefill: dict | None = None) -> None:
    st.session_state.edit_target = target
    st.session_state.delete_target = None
    st.session_state.prefill = prefill
    st.rerun()


# ── 工具列 ──────────────────────────────────────────────
if st.session_state.edit_target is None:
    col_l, col_r0, col_r1, col_r2 = st.columns([3, 1, 1, 1])
    with col_l:
        st.write("")
    with col_r0:
        if st.button("🌐 安裝外部 Skill", use_container_width=True, help="從 GitHub repo、任意 URL、貼上內容、上傳檔案 4 種來源安裝"):
            _switch_to("__github__")
    with col_r1:
        if st.button("📋 從範本", use_container_width=True, help="從現成範本一鍵建立 skill"):
            _switch_to("__templates__")
    with col_r2:
        if st.button("➕ 從零開始", type="primary", use_container_width=True):
            _switch_to("__new__")
else:
    col_l, col_r2 = st.columns([5, 1])
    with col_l:
        st.write("")
    with col_r2:
        if st.button("← 返回列表", use_container_width=True):
            _switch_to(None)

st.divider()


# ── 安裝外部 Skill（4 種來源）─────────────────────────────
def _render_safety_block(safety) -> None:
    if safety.dangers:
        st.error("🚨 **安全檢查未通過** — 偵測到危險指令，建議不要安裝：")
        for d in safety.dangers:
            st.markdown(f"- {d}")
    if safety.warnings:
        st.warning("⚠️ **注意事項**（不一定危險，但請留意）：")
        for w in safety.warnings:
            st.markdown(f"- {w}")
    if safety.is_safe and not safety.warnings:
        st.success("✅ **安全檢查通過** — 未偵測到危險指令。")


def _render_single_preview_and_install(result: FetchedSkill, *, ctx_key: str) -> None:
    """單一 SKILL.md 的預覽 + 安裝（共用給 4 個 tab）"""
    if result.fetch_error:
        st.error(f"❌ {result.fetch_error}")
        return

    _render_safety_block(result.safety)
    st.markdown("##### 📄 Skill 內容預覽")

    preview_name = st.text_input(
        "🏷️ 名稱（可修改）",
        value=result.name,
        placeholder="例如：code-review",
        key=f"{ctx_key}-name",
        help="安裝後用 `/名稱` 觸發",
    )
    preview_desc = st.text_input(
        "📝 描述（可修改）",
        value=result.description,
        placeholder="例如：對 git diff 做完整程式碼審查",
        key=f"{ctx_key}-desc",
    )
    tab1, tab2 = st.tabs(["👀 預覽", "📝 原始碼"])
    with tab1:
        st.markdown(result.body)
    with tab2:
        st.code(result.raw_content, language="markdown")

    st.markdown("")
    c1, c2, _ = st.columns([1, 1, 4])
    with c1:
        if st.button(
            "✅ 確認安裝" if result.safety.is_safe else "🚫 不建議安裝",
            type="primary",
            disabled=not result.safety.is_safe,
            use_container_width=True,
            key=f"{ctx_key}-install",
        ):
            _do_install(preview_name, preview_desc, result.body, ctx_key=ctx_key)
    with c2:
        if result.safety.dangers:
            if st.button("⚠️ 我了解風險，仍要安裝", use_container_width=True, key=f"{ctx_key}-force"):
                _do_install(preview_name, preview_desc, result.body, ctx_key=ctx_key, force=True)


def _do_install(name: str, desc: str, body: str, *, ctx_key: str, force: bool = False) -> None:
    if not validate_name(name):
        st.error("❌ 名稱不合法。只能用小寫英數字、底線、連字號。")
        return
    if not desc.strip():
        st.error("❌ 描述不能空白。")
        return
    try:
        save_skill(name=name.strip(), description=desc.strip(), body=body)
    except Exception as e:
        st.error(f"安裝失敗：{e}")
        return
    if force:
        st.warning(f"⚠️ 已強制安裝 `{name}`，請自行確認安全性。")
    else:
        st.success(f"🎉 已安裝 `{name}`！在 Claude Code 輸入 `/{name}` 即可使用。")
        st.balloons()
    st.session_state.github_result = None
    st.session_state[f"sel-{ctx_key}"] = set()


def _render_collection_picker(coll: SkillCollection, *, ctx_key: str) -> None:
    """集合 repo：列出所有 SKILL.md 給使用者勾選 + 批次安裝"""
    if coll.fetch_error and not coll.candidates:
        st.error(f"❌ {coll.fetch_error}")
        return
    if coll.fetch_error:
        st.warning(coll.fetch_error)

    if not coll.candidates:
        st.info("這個 repo / 路徑下找不到任何 SKILL.md")
        return

    st.success(
        f"✅ 在 [`{coll.user}/{coll.repo}`](https://github.com/{coll.user}/{coll.repo}/tree/{coll.branch}"
        f"{('/' + coll.subpath) if coll.subpath else ''}) 找到 **{len(coll.candidates)}** 個 skill"
        f"（分支 `{coll.branch}`{('，路徑 `' + coll.subpath + '`') if coll.subpath else ''}）"
    )

    sel_key = f"sel-{ctx_key}"
    selected: set[str] = st.session_state.setdefault(sel_key, set())

    bcols = st.columns([1, 1, 4])
    with bcols[0]:
        if st.button("全選", key=f"{ctx_key}-all", use_container_width=True):
            st.session_state[sel_key] = {c.folder for c in coll.candidates}
            st.rerun()
    with bcols[1]:
        if st.button("全不選", key=f"{ctx_key}-none", use_container_width=True):
            st.session_state[sel_key] = set()
            st.rerun()
    with bcols[2]:
        if st.button(
            f"📦 安裝勾選的 {len(selected)} 個",
            type="primary",
            disabled=not selected,
            use_container_width=True,
            key=f"{ctx_key}-batch",
        ):
            _batch_install(coll, selected, ctx_key=ctx_key)
            return

    st.caption("勾選 → 展開可預覽 + 安全檢查 → 一次安裝多個。或單獨按「✅ 安裝這個」")

    for cand in coll.candidates:
        with st.container(border=True):
            row = st.columns([0.5, 4, 1])
            with row[0]:
                checked = st.checkbox(
                    "選",
                    value=cand.folder in selected,
                    key=f"chk-{ctx_key}-{cand.folder}",
                    label_visibility="collapsed",
                )
                if checked:
                    selected.add(cand.folder)
                else:
                    selected.discard(cand.folder)
            with row[1]:
                st.markdown(f"### 📂 `{cand.folder}`")
                st.caption(f"路徑：`{cand.path}`")
                if cand.fetched and cand.description:
                    st.write(cand.description)
            with row[2]:
                if st.button(
                    "🔎 預覽",
                    key=f"prev-{ctx_key}-{cand.folder}",
                    use_container_width=True,
                ):
                    hydrate_candidate(cand)
                    st.session_state[f"expand-{ctx_key}-{cand.folder}"] = True
                    st.rerun()

            if st.session_state.get(f"expand-{ctx_key}-{cand.folder}"):
                if not cand.fetched:
                    hydrate_candidate(cand)
                if cand.fetch_error:
                    st.error(cand.fetch_error)
                else:
                    _render_safety_block(cand.safety)
                    with st.expander("👀 內容預覽", expanded=False):
                        st.markdown(cand.body)
                    sub = st.columns([1, 1, 4])
                    with sub[0]:
                        if st.button(
                            "✅ 安裝這個",
                            key=f"one-{ctx_key}-{cand.folder}",
                            type="primary",
                            disabled=not cand.safety.is_safe,
                            use_container_width=True,
                        ):
                            _do_install(
                                cand.name or cand.folder,
                                cand.description or f"從 {coll.user}/{coll.repo} 安裝的 skill",
                                cand.body,
                                ctx_key=f"{ctx_key}-{cand.folder}",
                            )
                    with sub[1]:
                        if st.button("收起", key=f"hide-{ctx_key}-{cand.folder}", use_container_width=True):
                            st.session_state.pop(f"expand-{ctx_key}-{cand.folder}", None)
                            st.rerun()


def _batch_install(coll: SkillCollection, folders: set[str], *, ctx_key: str) -> None:
    installed = []
    blocked = []
    failed = []
    progress = st.progress(0.0, text=f"安裝中… 0 / {len(folders)}")
    folder_to_cand = {c.folder: c for c in coll.candidates}
    items = sorted(folders)
    for i, folder in enumerate(items, 1):
        cand = folder_to_cand.get(folder)
        if not cand:
            failed.append((folder, "找不到候選"))
            continue
        hydrate_candidate(cand)
        if cand.fetch_error:
            failed.append((folder, cand.fetch_error))
        elif not cand.safety.is_safe:
            blocked.append((folder, cand.safety.dangers))
        else:
            name = cand.name or folder
            try:
                save_skill(
                    name=name,
                    description=cand.description or f"從 {coll.user}/{coll.repo} 安裝",
                    body=cand.body,
                )
                installed.append(name)
            except Exception as e:
                failed.append((folder, str(e)))
        progress.progress(i / len(items), text=f"安裝中… {i} / {len(items)}")
    progress.empty()

    if installed:
        st.success(f"🎉 已安裝 {len(installed)} 個：" + ", ".join(f"`{n}`" for n in installed))
        st.balloons()
    if blocked:
        st.error(f"🚫 {len(blocked)} 個因安全檢查未通過跳過")
        for f, dangers in blocked:
            with st.expander(f"❌ `{f}` 的危險項目", expanded=False):
                for d in dangers:
                    st.markdown(f"- {d}")
    if failed:
        st.error(f"❌ {len(failed)} 個失敗")
        for f, msg in failed:
            st.markdown(f"- `{f}`：{msg}")
    st.session_state[f"sel-{ctx_key}"] = set()


def render_install() -> None:
    st.subheader("🌐 安裝外部 Skill")
    st.info(
        "在網路上看到好用的 skill？4 種來源任你選 — 都會自動跑**安全檢查**確認沒有 `rm -rf`、"
        "`curl | sh` 之類的危險指令，再讓你決定要不要裝。"
    )

    tab_search, tab_gh, tab_url, tab_paste, tab_file = st.tabs(
        ["🔎 找 skill", "🐙 GitHub", "🔗 任意 URL", "📋 貼上內容", "📁 上傳 .md 檔"]
    )

    # ── Tab: 按名稱搜尋 ──
    with tab_search:
        st.markdown(
            "**只記得 skill 名字、不知道在哪？** 在這裡搜尋 — 會先比對 Anthropic 官方 skills 集合，"
            "再 fallback 到 GitHub 上熱門的 SKILL.md repo（按 ⭐ 數排序）。"
        )
        sc1, sc2, sc3 = st.columns([4, 1, 1])
        with sc1:
            q = st.text_input(
                "🔎 名稱或關鍵字",
                placeholder="例：pdf / code-review / mcp",
                key="search-query",
                label_visibility="collapsed",
            )
        with sc2:
            do_search = st.button("搜尋", type="primary", use_container_width=True, key="search-go")
        with sc3:
            do_browse = st.button("瀏覽全部", use_container_width=True, key="search-browse")

        with st.expander("🔧 進階", expanded=False):
            include_gh = st.checkbox(
                "也搜尋 GitHub（star 排序，可能慢一點）",
                value=True,
                key="search-include-gh",
            )
            if st.button("♻️ 重新整理已知集合（清快取）", key="search-refresh"):
                hits = skill_directory.list_all_known(force_refresh=True)
                st.session_state["search_hits"] = hits
                st.success(f"已重新整理，找到 {len(hits)} 個官方 skill")

        if do_search and q.strip():
            with st.spinner("搜尋中…"):
                st.session_state["search_hits"] = skill_directory.search(
                    q, include_github_search=include_gh
                )
        elif do_browse:
            with st.spinner("讀取已知 skill 集合…"):
                st.session_state["search_hits"] = skill_directory.list_all_known()

        hits = st.session_state.get("search_hits", [])
        if hits:
            st.caption(f"找到 {len(hits)} 筆")
            for i, hit in enumerate(hits):
                with st.container(border=True):
                    h1, h2 = st.columns([5, 1])
                    with h1:
                        badge = "🟣 官方" if hit.source != "github-search" else "🌐 GitHub"
                        title = f"### `{hit.name}`  {badge}"
                        if hit.stars is not None:
                            title += f"  ⭐ {hit.stars:,}"
                        st.markdown(title)
                        if hit.description:
                            st.write(hit.description)
                        st.caption(f"來源：[{hit.install_url}]({hit.install_url})")
                    with h2:
                        if st.button(
                            "📥 抓來看",
                            key=f"search-pick-{i}",
                            type="primary",
                            use_container_width=True,
                        ):
                            with st.spinner("抓取中…"):
                                st.session_state.github_result = github_fetch(hit.install_url)
                                st.session_state.pop("sel-gh", None)
                            st.success("已送進「🐙 GitHub」分頁，請切過去確認後安裝")
        elif do_search or do_browse:
            st.info("沒有找到任何結果。試試別的關鍵字，或切到「🐙 GitHub」直接貼連結。")

    # ── Tab: GitHub ──
    with tab_gh:
        with st.expander("💡 支援哪些 GitHub 連結格式？", expanded=False):
            st.markdown(
                """
                | 格式 | 範例 | 行為 |
                |------|------|------|
                | 單一檔案 | `https://github.com/user/repo/blob/main/path/SKILL.md` | 抓那個檔案 |
                | 子資料夾 | `https://github.com/user/repo/tree/main/my-skill` | 該資料夾內找 SKILL.md |
                | Repo 根目錄 | `https://github.com/user/repo` | 自動偵測：單檔 or 集合 |
                | Clone URL | `https://github.com/user/repo.git` | 同上（.git 自動處理） |
                | Raw 連結 | `https://raw.githubusercontent.com/user/repo/main/SKILL.md` | 直接抓 |

                **集合 repo**（例如 [anthropics/skills](https://github.com/anthropics/skills)）會列出所有
                找到的 `SKILL.md`，可以勾選後批次安裝。
                """
            )
        url = st.text_input(
            "📎 GitHub 連結",
            placeholder="https://github.com/anthropics/skills.git",
            help="貼上任意 GitHub URL — repo 集合也支援",
            key="gh-url",
        )
        if st.button("🔍 抓取並檢查", type="primary", disabled=not url.strip(), key="gh-fetch"):
            with st.spinner("從 GitHub 抓取中…"):
                st.session_state.github_result = github_fetch(url)
                st.session_state.pop("sel-gh", None)

        result = st.session_state.github_result
        if isinstance(result, FetchedSkill):
            st.divider()
            _render_single_preview_and_install(result, ctx_key="gh")
        elif isinstance(result, SkillCollection):
            st.divider()
            _render_collection_picker(result, ctx_key="gh")

    # ── Tab: 任意 URL ──
    with tab_url:
        st.markdown(
            "把整個 SKILL.md 的網址貼過來 — 例如 Gist 的 raw、別人部落格上的 .md 連結等。"
        )
        url2 = st.text_input(
            "🔗 SKILL.md 完整網址",
            placeholder="https://gist.githubusercontent.com/user/.../raw/code-review.md",
            key="url-input",
        )
        if st.button("🔍 抓取並檢查", type="primary", disabled=not url2.strip(), key="url-fetch"):
            with st.spinner("抓取中…"):
                st.session_state["url_result"] = installer.from_raw_url(url2)
        r = st.session_state.get("url_result")
        if r:
            st.divider()
            _render_single_preview_and_install(r, ctx_key="url")

    # ── Tab: 貼上 ──
    with tab_paste:
        st.markdown(
            "**直接把 SKILL.md 內容複製貼過來** — 適合朋友傳給你、或網頁上看到一段現成的 skill。"
        )
        with st.expander("💡 SKILL.md 長什麼樣子？", expanded=False):
            st.code(
                "---\nname: code-review\ndescription: 對 git diff 做完整程式碼審查\n---\n\n"
                "# Code Review\n\n"
                "幫使用者審查目前 staged 的程式碼變更。\n"
                "1. 跑 `git diff --staged`\n"
                "2. 列出 5 個最重要的問題\n"
                "3. 給具體的修改建議\n",
                language="markdown",
            )
        pasted = st.text_area(
            "貼到這裡（含 frontmatter 更好；沒有也會盡量幫你抓名稱）",
            height=240,
            key="paste-input",
        )
        if st.button("🔍 解析並檢查", type="primary", disabled=not pasted.strip(), key="paste-fetch"):
            st.session_state["paste_result"] = installer.from_paste(pasted)
        r = st.session_state.get("paste_result")
        if r:
            st.divider()
            _render_single_preview_and_install(r, ctx_key="paste")

    # ── Tab: 上傳 ──
    with tab_file:
        st.markdown(
            "**直接上傳 .md / .markdown 純文字檔。** 上傳完按下面的按鈕進行解析。"
        )
        uploaded = st.file_uploader(
            "選擇 SKILL.md 檔案",
            type=["md", "markdown", "txt"],
            accept_multiple_files=False,
            key="file-uploader",
        )
        if uploaded is not None:
            if st.button("🔍 解析並檢查", type="primary", key="file-fetch"):
                st.session_state["file_result"] = installer.from_file_bytes(
                    uploaded.getvalue(), filename=uploaded.name
                )
        r = st.session_state.get("file_result")
        if r:
            st.divider()
            _render_single_preview_and_install(r, ctx_key="file")


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
            "1. 點右上「**🌐 安裝外部 Skill**」→ 從 GitHub / URL / 貼內容 / 上傳檔案 4 種來源裝\n"
            "2. 點「**📋 從範本**」選一個現成的（最快，1 分鐘搞定）\n"
            "3. 或點「**➕ 從零開始**」自己寫"
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
                    f"**下一步**：在 Claude Code 輸入 `/{new_name}` 就能用了。"
                )
                st.session_state.edit_target = None
                st.rerun()
            except Exception as e:
                st.error(f"儲存失敗：{e}")


# ── 渲染分發 ──────────────────────────────────────────────
target = st.session_state.edit_target
if target is None:
    render_list()
elif target == "__github__":
    render_install()
elif target == "__templates__":
    render_templates()
else:
    render_form(None if target == "__new__" else target)
