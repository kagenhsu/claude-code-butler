"""🔌 MCP — 新手友善版。

設計原則:
1. 首頁就是「我想讓 Claude 做什麼」的卡片區,點一下就能裝
2. 每張卡片都有明確的『權限 / 風險 / 依賴』(資安透明)
3. 技術詞(stdio / npx / args)收到「🔧 進階」expander 裡
4. 預設用全域;專案範圍是進階選項
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

import streamlit as st

from lib import mcp_directory as directory
from lib import mcp_store

st.set_page_config(page_title="MCP | Claude Code 管家", page_icon="🔌", layout="wide")

from lib.ui import inject_style  # noqa: E402
from lib.nav import render_nav  # noqa: E402

inject_style(st)
render_nav()

st.title("🔌 MCP — 給 Claude 裝外掛")
st.caption("MCP 是 Claude 的『外掛系統』。挑一個外掛 → 一鍵安裝 → 重啟 Claude Code 就能用")


# ╔═════════════════════════════════════════════════════════╗
# ║ 一句話教學 + 範圍狀態(預設全域,進階才切專案)         ║
# ╚═════════════════════════════════════════════════════════╝
with st.container(border=True):
    st.markdown(
        """
        ### 🤔 三句話搞懂 MCP

        1. **是什麼**:Claude 預設不能讀你的檔案、不能上網、不能查資料庫 — 是個純文字對話。
        2. **MCP 解決什麼**:給它「外掛」,每個外掛開放一種能力(讀檔、搜尋、查 DB...)。
        3. **怎麼用**:在下面挑你要的外掛 → 按「📥 安裝」→ **重啟 Claude Code** → 在 Claude Code 裡打 `/mcp` 可看清單。
        """
    )

# 範圍狀態(摺進去)
with st.expander("📂 套用範圍 — 預設全域;只在某專案要用才切「專案」", expanded=False):
    scope = st.radio(
        "範圍",
        ["🌐 全域(所有專案都吃得到)", "📁 專案(只給某個專案用)"],
        index=0, key="mcp-scope", horizontal=True,
    )
    project_dir = ""
    if "全域" in scope:
        settings_path: Path = mcp_store.global_settings_file()
        st.caption(f"✅ 寫到 `{settings_path}`(安全:會自動 backup 5 份)")
    else:
        from lib.hooks_store import find_candidate_projects
        candidates = find_candidate_projects()
        options = ["(手動輸入路徑)"] + [str(p) for p in candidates]
        sel = st.selectbox("選一個專案資料夾", options, key="mcp-proj-sel")
        if sel == "(手動輸入路徑)":
            project_dir = st.text_input(
                "輸入專案絕對路徑",
                placeholder="/Users/xujiayuan/work/my-project",
                key="mcp-proj-path",
            )
        else:
            project_dir = sel
        if not project_dir or not Path(project_dir).is_dir():
            st.warning("⚠️ 路徑無效,改用全域")
            settings_path = mcp_store.global_settings_file()
        else:
            settings_path = mcp_store.project_settings_file(project_dir)
            st.caption(f"✅ 寫到 `{settings_path}`(可 commit 到 git)")

# 預設全域(若沒打開上面 expander)
if "全域" in st.session_state.get("mcp-scope", "🌐 全域"):
    settings_path = mcp_store.global_settings_file()

scope_label = "全域" if "全域" in st.session_state.get("mcp-scope", "🌐 全域") else f"專案 `{project_dir}`"
servers = mcp_store.load_servers(settings_path)


# ╔═════════════════════════════════════════════════════════╗
# ║ 依賴自動偵測 — 缺什麼就告訴使用者怎麼裝                ║
# ╚═════════════════════════════════════════════════════════╝
needed_globally = list({p for s in directory.BUILTIN_SERVERS for p in s.get("needs_prereq", [])})
preq = directory.prereq_status(needed_globally)
missing = [p for p in preq if not p["installed"]]
if missing:
    with st.container(border=True):
        st.markdown("#### ⚙️ 偵測到缺少一些工具(裝了才能跑某些外掛)")
        for p in missing:
            st.markdown(f"**❌ {p['label']}** — {p['why_needed']}")
            st.code(p["install_hint"], language="bash")
        st.caption("缺工具的外掛還是可以看,但安裝前要先裝好對應工具。")
else:
    with st.container(border=True):
        st.success("✅ 依賴工具齊全:" + " / ".join(f"`{p['label']}`" for p in preq))


# ╔═════════════════════════════════════════════════════════╗
# ║ 安裝動作 + 表單                                         ║
# ╚═════════════════════════════════════════════════════════╝
def _risk_badge(level: str) -> str:
    meta = directory.RISK_META.get(level, {})
    return f"{meta.get('emoji', '⚪')} {meta.get('label', level)}"


def _do_install(name: str, config: dict, *, allow_overwrite: bool = False) -> bool:
    """寫進 settings。回傳是否成功。"""
    try:
        mcp_store.add_server(settings_path, name, config, overwrite=allow_overwrite)
        st.success(
            f"✅ 已安裝 `{name}` 到 {scope_label}。"
            f"**請完全結束 Claude Code、重新啟動 session 後生效**(打 `/mcp` 確認)。"
        )
        st.balloons()
        return True
    except ValueError as e:
        msg = str(e)
        if "已存在" in msg:
            st.warning(msg)
            if st.button(f"覆蓋既有 `{name}`", key=f"ov-{name}", type="primary"):
                mcp_store.add_server(settings_path, name, config, overwrite=True)
                st.success(f"✅ 已覆蓋 `{name}`")
                st.rerun()
        else:
            st.error(msg)
    except Exception as e:
        st.error(f"❌ 寫入失敗:{e}")
    return False


def render_install_form(entry: dict, *, key_prefix: str) -> None:
    """卡片下方:展開的安裝表單(動態根據 params 生欄位)。"""
    # 先檢查依賴
    pq = directory.prereq_status(entry.get("needs_prereq", []))
    not_ready = [p for p in pq if not p["installed"]]
    if not_ready:
        st.warning(
            "⚠️ 安裝前要先裝這些:" + ", ".join(f"`{p['label']}`" for p in not_ready)
        )
        for p in not_ready:
            st.code(p["install_hint"], language="bash")
        st.caption("裝完之後重整這頁。")

    with st.form(key=f"form-{key_prefix}"):
        st.markdown(f"##### 設定 `{entry['name']}`")
        custom_name = st.text_input(
            "在 Claude Code 內顯示的名字",
            value=entry["name"], key=f"name-{key_prefix}",
            help="可以改成自己看得懂的名字,例如 `my-files`",
        )
        # 動態 params
        param_values: dict[str, str] = {}
        for p in entry.get("params", []):
            widget_kwargs = {
                "key": f"{key_prefix}-{p['key']}",
                "placeholder": p.get("placeholder", ""),
                "help": p.get("hint", ""),
            }
            label = p["label"] + ("(必填)" if p.get("required") else "")
            if p.get("kind") == "password":
                widget_kwargs["type"] = "password"
            param_values[p["key"]] = st.text_input(label, **widget_kwargs)

        c1, c2 = st.columns(2)
        with c1:
            go = st.form_submit_button(
                "✅ 確認安裝",
                type="primary",
                use_container_width=True,
                disabled=bool(not_ready),
            )
        with c2:
            cancel = st.form_submit_button("取消", use_container_width=True)
        if go:
            try:
                cfg = directory.materialize_builtin(entry, param_values)
                if _do_install(custom_name, cfg):
                    st.session_state[f"open-{key_prefix}"] = False
            except ValueError as ve:
                st.error(str(ve))
        if cancel:
            st.session_state[f"open-{key_prefix}"] = False
            st.rerun()


def render_card(entry: dict, *, key_prefix: str) -> None:
    """新手友善的 server 卡片。"""
    installed_already = entry["name"] in servers
    risk = entry.get("risk_level", "low")
    with st.container(border=True):
        h1, h2 = st.columns([5, 1])
        with h1:
            title = f"### {entry.get('newbie_title', entry['label'])}"
            if installed_already:
                title += "  ✅ 已安裝"
            st.markdown(title)
            st.markdown(f"_{entry.get('what_it_does', '')}_")
            st.caption(f"💡 **適合**:{entry.get('good_for', '—')}")
        with h2:
            if installed_already:
                st.success("已裝", icon="✅")
            else:
                if st.button(
                    "📥 安裝",
                    key=f"open-btn-{key_prefix}",
                    type="primary",
                    use_container_width=True,
                ):
                    st.session_state[f"open-{key_prefix}"] = True
                    st.rerun()

        # 資安行
        rb = _risk_badge(risk)
        pq = directory.prereq_status(entry.get("needs_prereq", []))
        prereq_str = " · ".join(
            f"{'✅' if p['installed'] else '❌'} {p['label']}" for p in pq
        ) or "✅ 無需特別依賴"
        st.markdown(f"**🛡️ 權限**:{entry.get('permissions', '—')}　|　**{rb}**　|　**📦** {prereq_str}")

        # 詳情(摺起)
        with st.expander("ℹ️ 看詳細安全提醒 / 技術細節", expanded=False):
            st.markdown("**🔒 安全提醒:**")
            for s in entry.get("security_notes", []):
                st.markdown(f"- {s}")
            st.markdown(f"**🏷️ 標籤**:{', '.join(entry.get('tags', []))}")
            st.markdown(f"**💻 啟動命令**:")
            cmd_preview = entry["command"] + " " + " ".join(entry.get("args_template", []))
            st.code(cmd_preview + "  <你的參數>", language="bash")

        # 已安裝 → 顯示移除 + 重設
        if installed_already:
            ac1, ac2, _ = st.columns([1, 1, 4])
            with ac1:
                if st.button("🔧 重新設定", key=f"re-{key_prefix}", use_container_width=True):
                    mcp_store.delete_server(settings_path, entry["name"])
                    st.session_state[f"open-{key_prefix}"] = True
                    st.rerun()
            with ac2:
                if st.button("🗑️ 移除", key=f"rm-{key_prefix}", use_container_width=True):
                    mcp_store.delete_server(settings_path, entry["name"])
                    st.rerun()

        # 安裝表單(打開時)
        if st.session_state.get(f"open-{key_prefix}"):
            st.divider()
            render_install_form(entry, key_prefix=key_prefix)


# ╔═════════════════════════════════════════════════════════╗
# ║ 主入口:我想讓 Claude 做什麼?                          ║
# ╚═════════════════════════════════════════════════════════╝
st.markdown("## 🎯 我想讓 Claude…")

sec_tab_general, sec_tab_dev = st.tabs(["👤 一般使用", "👨‍💻 開發者"])

with sec_tab_general:
    st.caption("最常用的 5 個外掛,日常工作就用這幾個。")
    for entry in directory.by_category("general"):
        render_card(entry, key_prefix=f"gen-{entry['id']}")

with sec_tab_dev:
    st.caption("開發場景:Git、GitHub、資料庫、瀏覽器自動化、Slack…")
    for entry in directory.by_category("dev"):
        render_card(entry, key_prefix=f"dev-{entry['id']}")


# ╔═════════════════════════════════════════════════════════╗
# ║ 目前裝了什麼(若有才顯示)                              ║
# ╚═════════════════════════════════════════════════════════╝
if servers:
    st.divider()
    st.markdown("## 📋 你目前裝了這些")
    st.caption(f"共 {len(servers)} 個 server 在 {scope_label}")
    for name, conf in servers.items():
        with st.container(border=True):
            kind = mcp_store.server_kind(conf)
            kind_emoji = "🖥️" if kind == "stdio" else "🌐"
            h1, h2 = st.columns([5, 1])
            with h1:
                st.markdown(f"### {kind_emoji} `{name}`")
                st.code(mcp_store.describe_server(conf), language="bash")
                if conf.get("env"):
                    masked = {k: ("***" if any(s in k.upper() for s in ("KEY", "TOKEN", "SECRET", "PASS")) else v)
                              for k, v in conf["env"].items()}
                    st.caption("env: " + ", ".join(f"`{k}={v}`" for k, v in masked.items()))
            with h2:
                if st.button("🧪 連線測試", key=f"l-test-{name}", use_container_width=True):
                    with st.spinner("連線中…(最多 6 秒)"):
                        st.session_state[f"l-tr-{name}"] = mcp_store.try_spawn_server(conf)
                    st.rerun()
                if st.button("🗑️ 移除", key=f"l-del-{name}", use_container_width=True):
                    mcp_store.delete_server(settings_path, name)
                    st.rerun()
            tr = st.session_state.get(f"l-tr-{name}")
            if tr:
                (st.success if tr["ok"] else st.error)(tr["msg"])
                if tr.get("details"):
                    with st.expander("詳情"):
                        st.code(tr["details"], language="text")


# ╔═════════════════════════════════════════════════════════╗
# ║ 進階(摺起):搜尋 / 官方目錄 / GitHub URL / 手動 / JSON║
# ╚═════════════════════════════════════════════════════════╝
st.divider()
st.markdown("## 🔧 進階")
st.caption("找其他冷門 server、從 GitHub 直接抓、手刻設定...這裡。新手不用點進去。")

adv = st.expander("展開進階選項", expanded=False)
with adv:
    adv_tabs = st.tabs(
        ["🔎 關鍵字搜尋(含 npm 下載量)", "📚 官方目錄全表", "🐙 從 GitHub repo URL", "✍️ 手動 / 貼 JSON"]
    )

    # ── 進階 Tab 1: 搜尋 ──
    with adv_tabs[0]:
        st.markdown("關鍵字模糊搜尋,先比對內建,不夠再 fallback 到 **npm registry**(會抓上週下載量,熱門優先)")
        c1, c2 = st.columns([4, 1])
        with c1:
            q = st.text_input("關鍵字", placeholder="例:filesystem / github / 資料庫 / browser",
                              key="adv-q", label_visibility="collapsed")
        with c2:
            inc_npm = st.checkbox("含 npm", value=True, key="adv-npm")
        if st.button("搜尋", key="adv-go", type="primary"):
            with st.spinner("搜尋中…"):
                st.session_state["adv_hits"] = directory.search(q, include_npm=inc_npm)
        for i, hit in enumerate(st.session_state.get("adv_hits", [])):
            with st.container(border=True):
                badge = "🟣 內建" if hit.source == "builtin" else "📦 npm"
                title = f"### `{hit.name}`  {badge}"
                if hit.downloads_weekly is not None:
                    title += f"  📥 {hit.downloads_weekly:,}/週"
                st.markdown(title)
                if hit.description:
                    st.write(hit.description)
                if hit.source == "npm":
                    st.code(hit.install_command or "", language="bash")
                    if st.button("📋 帶到「手動 / 貼 JSON」", key=f"adv-cp-{i}"):
                        st.session_state["manual-prefill-json"] = json.dumps(
                            {hit.name.split("/")[-1].replace("server-", ""):
                             {"command": "npx", "args": ["-y", hit.name]}},
                            ensure_ascii=False, indent=2,
                        )
                        st.success("已帶到「手動 / 貼 JSON」分頁")
                elif hit.builtin_entry:
                    if st.button("📥 直接安裝", key=f"adv-i-{i}", type="primary"):
                        st.session_state[f"open-adv-{hit.name}"] = True
                        st.rerun()
                    if st.session_state.get(f"open-adv-{hit.name}"):
                        render_install_form(hit.builtin_entry, key_prefix=f"adv-{hit.name}")

    # ── 進階 Tab 2: 官方目錄 ──
    with adv_tabs[1]:
        st.markdown(
            "**Anthropic 官方 monorepo:[modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers)**"
            " 裡 `src/*` 底下所有 server。"
        )
        c1, c2 = st.columns([1, 5])
        with c1:
            refresh = st.button("♻️ 刷新", key="off-refresh")
        if "off_items" not in st.session_state or refresh:
            with st.spinner("從 GitHub 抓官方清單…"):
                st.session_state["off_items"] = directory.fetch_official_servers(force_refresh=refresh)
        items = st.session_state.get("off_items", [])
        if not items:
            st.warning("拿不到官方清單(GitHub API 可能 rate limit,等一下再試)")
        else:
            st.caption(f"共 {len(items)} 個 — 內建已涵蓋的會直接連到該卡片")
            builtin_names = {s["name"] for s in directory.BUILTIN_SERVERS}
            for it in items:
                with st.container(border=True):
                    c1, c2 = st.columns([5, 1])
                    with c1:
                        st.markdown(f"**`{it['name']}`** — [GitHub 頁面]({it['github_url']})")
                        npm_pkg = f"@modelcontextprotocol/server-{it['name']}"
                        st.code(f"npx -y {npm_pkg}", language="bash")
                        if it["name"] in builtin_names:
                            st.caption("✅ 已收錄在內建卡片(到上面「我想讓 Claude…」分類找)")
                    with c2:
                        if st.button("📋 帶到 JSON", key=f"off-cp-{it['name']}",
                                     use_container_width=True):
                            st.session_state["manual-prefill-json"] = json.dumps(
                                {it["name"]: {"command": "npx", "args": ["-y", npm_pkg]}},
                                ensure_ascii=False, indent=2,
                            )
                            st.success("已帶到「手動 / 貼 JSON」分頁")

    # ── 進階 Tab 3: GitHub URL ──
    with adv_tabs[2]:
        st.markdown(
            "**給任何 GitHub MCP server 的 URL**,我會抓 README 把可能的安裝設定挖出來。"
        )
        url = st.text_input(
            "GitHub repo URL",
            placeholder="https://github.com/某人/某個-mcp-server",
            key="gh-mcp-url",
        )
        if st.button("🔍 解析", key="gh-mcp-go", type="primary", disabled=not url.strip()):
            with st.spinner("抓 README + 分析…"):
                st.session_state["gh_hint"] = directory.from_github_repo(url)
        hint = st.session_state.get("gh_hint")
        if hint:
            if hint.fetch_error:
                st.error(hint.fetch_error)
            else:
                st.success(
                    f"[`{hint.user}/{hint.repo}`]({hint.readme_url.rsplit('/', 1)[0]})"
                    + (f"  ⭐ {hint.stars:,}" if hint.stars else "")
                    + (f"  · README 提到 MCP ✓" if hint.has_mcp_keyword else "  · 沒提到 MCP ⚠️")
                )
                for n in hint.notes:
                    st.warning(n)
                if hint.json_configs:
                    st.markdown(f"#### 🎯 找到 {len(hint.json_configs)} 個可能的設定")
                    for i, conf in enumerate(hint.json_configs):
                        suggested_name = conf.pop("_suggested_name", f"{hint.repo}-{i}")
                        with st.container(border=True):
                            st.markdown(f"**建議名稱:`{suggested_name}`**")
                            st.code(json.dumps(conf, ensure_ascii=False, indent=2), language="json")
                            cc1, cc2 = st.columns([1, 1])
                            with cc1:
                                if st.button("📥 直接安裝", key=f"gh-inst-{i}", type="primary"):
                                    _do_install(suggested_name, conf)
                            with cc2:
                                if st.button("📋 帶到 JSON 編輯", key=f"gh-cp-{i}"):
                                    st.session_state["manual-prefill-json"] = json.dumps(
                                        {suggested_name: conf}, ensure_ascii=False, indent=2,
                                    )
                                    st.success("已帶到「手動 / 貼 JSON」分頁")
                if hint.install_commands and not hint.json_configs:
                    st.markdown("#### 找到的安裝指令(沒有 JSON 範例)")
                    for c in hint.install_commands:
                        st.code(c, language="bash")
                if hint.raw_json_blocks:
                    with st.expander("README 裡的 JSON 區塊原文", expanded=False):
                        for b in hint.raw_json_blocks:
                            st.code(b, language="json")

    # ── 進階 Tab 4: 手動 / 貼 JSON ──
    with adv_tabs[3]:
        st.markdown("**從別處複製的 JSON / 自己手刻** — 適合 power user。")
        j = st.text_area(
            "貼 JSON(支援 `{name: {...}}` 或 `{mcpServers: {name: {...}}}`)",
            value=st.session_state.get("manual-prefill-json", ""),
            height=240,
            key="json-paste",
            placeholder='{\n  "filesystem": {\n    "command": "npx",\n    "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/me/Documents"]\n  }\n}',
        )
        if st.button("📥 解析並安裝", type="primary", disabled=not j.strip(), key="json-go"):
            try:
                parsed = json.loads(j)
            except json.JSONDecodeError as e:
                st.error(f"❌ JSON 格式錯誤:{e}")
            else:
                items = parsed.get("mcpServers") if isinstance(parsed, dict) and "mcpServers" in parsed else parsed
                if not isinstance(items, dict):
                    st.error("❌ JSON 必須是 object")
                else:
                    ok = 0
                    for n, c in items.items():
                        try:
                            mcp_store.add_server(settings_path, n, c, overwrite=True)
                            ok += 1
                        except Exception as e:
                            st.error(f"`{n}` 失敗:{e}")
                    if ok:
                        st.success(f"✅ 安裝 {ok} 個 server 到 {scope_label}")
                        st.session_state.pop("manual-prefill-json", None)
                        st.balloons()
                        st.rerun()


# ╔═════════════════════════════════════════════════════════╗
# ║ 故障排除 + raw 設定                                     ║
# ╚═════════════════════════════════════════════════════════╝
with st.expander("🆘 裝了沒效果?點開看故障排除", expanded=False):
    st.markdown(
        """
        **裝了但 Claude Code 看不到?**
        → MCP 設定只在 session 啟動時讀。**完全結束 Claude Code 再重開**。
        → 重開後在 Claude Code 內打 `/mcp` 或在終端打 `claude mcp list`。

        **連線測試「找不到指令」?**
        → 缺 `npx`(要先裝 Node.js)或 `uvx`(要 `pip install uv`)。上方依賴區會自動提醒。

        **連線測試「超時沒回應」?**
        → 多半是第一次跑時 `npx` 在背景下載 package(可能要好幾十秒)。
        → 在終端機先手動跑一次完整指令把套件預載,回來再測。

        **想刪掉?**
        → 在「📋 你目前裝了這些」按「🗑️ 移除」即可。每次寫入都會自動 backup 5 份在
          `~/.claude.json.bak.*`,誤刪可還原。

        **API Key / Token 安全嗎?**
        → 會明文寫進 `~/.claude.json`,該檔權限是 600(只有你自己能讀)。
        → 若擔心,Token 用後到原平台撤銷重發即可。

        **要分享某個專案專屬的 MCP 給同事?**
        → 上方範圍切到「📁 專案」,會寫到 `<project>/.mcp.json`,可以 commit 到 git。
        """
    )

with st.expander("🔧 看 raw mcpServers JSON", expanded=False):
    raw = mcp_store.load_servers(settings_path)
    st.code(json.dumps(raw, ensure_ascii=False, indent=2), language="json")
