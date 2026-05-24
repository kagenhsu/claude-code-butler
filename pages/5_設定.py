"""⚙️ 設定 — 系統資訊、硬體規格、使用量、主題 / 預設模型 / 備份還原"""
from __future__ import annotations

import json
import platform
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st

from lib import theme as theme_lib, backup as backup_lib
from lib.paths import (
    claude_dir,
    config_file,
    settings_file,
    user_skills_dir,
)
from lib.hardware import detect_hardware, estimate_task_capacity
from lib.usage import MODEL_INFO, detect_usage

st.set_page_config(page_title="設定 | Claude Code 管家", page_icon="⚙️", layout="wide")

from lib.ui import inject_style
from lib.nav import render_nav
inject_style(st)
render_nav()

st.title("⚙️ 設定")
st.caption("硬體規格、使用量、系統路徑")

# ── 偵測 ──
spec = detect_hardware()
capacity = estimate_task_capacity(spec)
usage = detect_usage()

# ── 硬體規格 ──────────────────────────────────────────────
st.subheader("🖥️ 電腦硬體規格")

with st.container(border=True):
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("CPU", f"{spec.cpu_cores} 核心", help=spec.cpu_name)
    with c2:
        st.metric("記憶體", f"{spec.ram_total_gb} GB", help=f"可用 {spec.ram_available_gb} GB（已用 {spec.ram_used_percent}%）")
    with c3:
        gpu_label = spec.gpu_name or "未偵測到"
        st.metric("GPU", f"{spec.gpu_cores} 核心" if spec.gpu_cores else "—", help=gpu_label)
    with c4:
        st.metric("磁碟空間", f"{spec.disk_free_gb:.0f} GB 可用", help=f"總共 {spec.disk_total_gb:.0f} GB（已用 {spec.disk_used_percent}%）")

# ── 資源使用率 ──
with st.container(border=True):
    st.markdown("**📊 資源使用率**")
    r1, r2, r3 = st.columns(3)
    with r1:
        st.progress(min(spec.ram_used_percent / 100, 1.0), text=f"記憶體 {spec.ram_used_percent}%")
    with r2:
        st.progress(min(spec.disk_used_percent / 100, 1.0), text=f"磁碟 {spec.disk_used_percent}%")
    with r3:
        if spec.ram_used_percent > 80:
            st.warning("⚠️ 記憶體使用率偏高")
        elif spec.disk_used_percent > 90:
            st.warning("⚠️ 磁碟空間不足")
        else:
            st.success("✅ 資源充足")

st.divider()

# ── 任務容量估算 ──────────────────────────────────────────
st.subheader("🤖 自動化任務容量")

with st.container(border=True):
    t1, t2 = st.columns([1, 2])
    with t1:
        st.metric(
            "可同時執行",
            f"{capacity.max_concurrent} 個任務",
            help=f"每個 Claude Code 任務約需 {capacity.ram_per_task_mb} MB 記憶體",
        )
    with t2:
        st.markdown(f"""
| 項目 | 數值 |
|------|------|
| **瓶頸** | {capacity.bottleneck} |
| **每個任務所需記憶體** | ~{capacity.ram_per_task_mb} MB |
| **可用記憶體** | {spec.ram_available_gb} GB |
| **可用 CPU 核心** | {max(1, spec.cpu_cores - 2)}（保留 2 個給系統） |
""")
    if capacity.recommendation:
        st.info(f"💡 {capacity.recommendation}")

st.divider()

# ── 模型與方案 ──────────────────────────────────────────────
st.subheader("🧠 大語言模型使用狀態")

with st.container(border=True):
    m1, m2, m3 = st.columns(3)
    with m1:
        st.metric("目前模型", usage.model_display, help=f"模型 ID：{usage.model_id}")
    with m2:
        st.metric("模型等級", usage.model_tier, help="旗艦 > 進階 > 快速")
    with m3:
        st.metric("上下文長度", usage.context_window, help="單次對話可處理的最大 token 數")

with st.container(border=True):
    st.markdown(f"""
| 項目 | 狀態 |
|------|------|
| **訂閱方案** | {usage.plan_name} |
| **方案說明** | {usage.plan_details} |
| **今日 Session 數** | {usage.sessions_today} |
| **歷史 Session 總數** | {usage.sessions_total} |
| **今日對話次數** | {usage.history_entries_today} |
| **目前活躍 Session** | {usage.active_sessions} |
""")

    if usage.detection_notes:
        for note in usage.detection_notes:
            st.caption(f"ℹ️ {note}")

# ── 方案比較 ──
with st.expander("📋 Claude Code 方案比較", expanded=False):
    st.markdown("""
| 方案 | 月費 | 模型 | 上下文 | 速率 |
|------|------|------|--------|------|
| Free | 免費 | Sonnet | 200K | 基礎 |
| Pro | $20/月 | Sonnet + Opus（有限） | 200K | 5 倍 |
| Max 5x | $100/月 | Opus + Sonnet | 1M | 5 倍 |
| Max 20x | $200/月 | Opus + Sonnet | 1M | 20 倍 |

> **速率**指的是每分鐘可以送出多少請求。20 倍速率適合大量自動化任務。

> Claude Code 訂閱制的用量上限是動態調整的，無法從本地精確查詢剩餘額度。
> 如果遇到速率限制，通常等幾分鐘就會恢復。
""")

st.divider()

# ── 路徑 ──────────────────────────────────────────────
st.subheader("📁 系統路徑")
with st.container(border=True):
    st.write(f"**Home**：`{Path.home()}`")
    st.write(f"**Claude Code 目錄**：`{claude_dir()}`")
    st.write(f"**Skills 目錄**：`{user_skills_dir()}`")
    st.write(f"**管家設定檔**：`{config_file()}`（v2）")
    st.write(f"**Python**：`{sys.version.split()[0]}`")
    st.write(f"**作業系統**：{platform.system()} {platform.release()} ({platform.machine()})")

st.divider()

# ── 進階設定 ──────────────────────────────────────────────
st.subheader("⚙️ 進階設定")

tab_theme, tab_model, tab_backup = st.tabs([
    "🎨 主題",
    "🎯 預設模型",
    "📦 備份與還原",
])

st.caption(
    "💡 API Key 管理請到 [🤖 雲端模型](/雲端模型) 頁面；"
    "金鑰已自動以本機綁定主密鑰加密儲存。"
)

# ───────── 🎨 主題切換 ─────────
with tab_theme:
    st.markdown("切換管家介面的明暗主題。")

    current_theme = theme_lib.get_theme()
    theme_keys = list(theme_lib.THEMES.keys())
    current_idx = theme_keys.index(current_theme) if current_theme in theme_keys else 2

    cols = st.columns(len(theme_keys))
    for i, key in enumerate(theme_keys):
        info = theme_lib.THEMES[key]
        with cols[i]:
            label = f"{info['icon']} {info['label']}"
            if key == current_theme:
                label = f"✓ {label}"
            if st.button(label, key=f"theme-{key}", use_container_width=True,
                         type="primary" if key == current_theme else "secondary"):
                theme_lib.set_theme(key)
                st.success(f"✅ 已切換到「{info['label']}」")
                st.info("💡 請重新整理頁面（⌘R / Ctrl+R）讓主題生效")
                st.rerun()

    st.caption(f"目前設定：**{theme_lib.THEMES[current_theme]['label']}**")
    st.caption(
        "Streamlit 啟動時才會讀主題設定，切換後需要重新整理頁面或重啟服務。"
    )

# ───────── 🎯 預設模型切換 ─────────
with tab_model:
    st.markdown(
        "設定 Claude Code 預設使用的模型。"
        "這會寫入 `~/.claude/settings.json` 的 `model` 欄位。"
    )

    sf = settings_file()
    current_model = ""
    settings_data: dict = {}
    if sf.is_file():
        try:
            settings_data = json.loads(sf.read_text(encoding="utf-8"))
            current_model = settings_data.get("model", "")
        except Exception:
            settings_data = {}

    model_ids = list(MODEL_INFO.keys())
    options = ["（讓 Claude Code 自己決定）"] + [
        f"{mid} — {MODEL_INFO[mid]['display']}（{MODEL_INFO[mid]['tier']}・{MODEL_INFO[mid]['context']}）"
        for mid in model_ids
    ]

    if current_model in model_ids:
        idx = model_ids.index(current_model) + 1
    else:
        idx = 0

    selected = st.selectbox("預設模型", options, index=idx, key="default-model-select")

    if selected == options[0]:
        chosen_id = ""
    else:
        chosen_id = model_ids[options.index(selected) - 1]

    b1, b2, _ = st.columns([1, 1, 3])
    with b1:
        if st.button("💾 套用", type="primary", use_container_width=True, key="model-save"):
            sf.parent.mkdir(parents=True, exist_ok=True)
            data = settings_data.copy() if settings_data else {}
            if chosen_id:
                data["model"] = chosen_id
            else:
                data.pop("model", None)
            sf.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            if chosen_id:
                st.success(f"✅ 預設模型已設為 `{chosen_id}`")
            else:
                st.success("✅ 已清除預設模型（交給 Claude Code 自動選擇）")
            st.rerun()
    with b2:
        if current_model and st.button("🔄 重置", use_container_width=True, key="model-reset"):
            data = settings_data.copy()
            data.pop("model", None)
            sf.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            st.success("✅ 已清除預設模型")
            st.rerun()

    if current_model:
        info = MODEL_INFO.get(current_model)
        if info:
            st.caption(f"目前：**{info['display']}**（{info['tier']}・上下文 {info['context']}）")
        else:
            st.caption(f"目前：`{current_model}`（未知模型）")
    else:
        st.caption("目前：未設定（Claude Code 將使用內建預設值）")

# ───────── 📦 備份與還原 ─────────
with tab_backup:
    st.markdown("把 Skills、設定、Prompt 庫打包成 zip，方便換機或備份。")

    sub_export, sub_import = st.tabs(["📤 匯出備份", "📥 還原備份"])

    with sub_export:
        st.markdown("**選擇要備份的項目：**")
        selected_items: list[str] = []
        for item_id, spec in backup_lib.BACKUP_ITEMS.items():
            path = spec["path"]()
            exists = path.exists()
            default = exists
            label = f"{spec['icon']} {spec['label']}"
            if not exists:
                label += "（找不到，無法備份）"
            checked = st.checkbox(
                label,
                value=default,
                key=f"backup-pick-{item_id}",
                disabled=not exists,
            )
            if checked and exists:
                selected_items.append(item_id)

        if selected_items:
            if st.button("📦 產生備份檔", type="primary", key="backup-build"):
                with st.spinner("打包中..."):
                    zip_bytes = backup_lib.create_backup(selected_items)
                fname = f"aihub-backup-{datetime.now().strftime('%Y%m%d-%H%M%S')}.zip"
                st.download_button(
                    "⬇️ 下載備份檔",
                    data=zip_bytes,
                    file_name=fname,
                    mime="application/zip",
                    type="primary",
                    key="backup-download",
                )
                st.success(f"✅ 已打包 {len(selected_items)} 個項目，大小 {len(zip_bytes)/1024:.1f} KB")
        else:
            st.info("請至少勾選一項要備份的內容")

        st.caption(
            "🔒 API Key 是用本機綁定的主密鑰加密的，主密鑰**不會**放進備份檔。"
            "還原到同一台機器可正常解開；還原到別台機器後，"
            "請到 [🤖 雲端模型](/雲端模型) 頁面重新輸入 Key。"
        )

    with sub_import:
        uploaded = st.file_uploader(
            "選擇備份 zip",
            type=["zip"],
            key="backup-upload",
        )

        if uploaded is not None:
            zip_bytes = uploaded.read()
            info = backup_lib.inspect_backup(zip_bytes)

            if "error" in info:
                st.error(f"❌ {info['error']}")
            else:
                manifest = info["manifest"]
                counts = info["counts"]
                with st.container(border=True):
                    st.markdown(f"**備份檔產生時間**：{manifest.get('created_at', '未知')}")
                    items_in_backup = manifest.get("items", [])
                    st.markdown("**內容：**")
                    chosen: list[str] = []
                    for iid in items_in_backup:
                        spec = backup_lib.BACKUP_ITEMS.get(iid)
                        if not spec:
                            st.caption(f"⚠️ 未知項目：{iid}（無法還原）")
                            continue
                        n = counts.get(iid, 0)
                        c = st.checkbox(
                            f"{spec['icon']} {spec['label']}（{n} 個檔案）",
                            value=True,
                            key=f"restore-pick-{iid}",
                        )
                        if c:
                            chosen.append(iid)

                overwrite = st.checkbox(
                    "覆寫已存在的檔案",
                    value=False,
                    key="restore-overwrite",
                    help="勾起來才會覆寫；不勾就會跳過已存在的檔案。",
                )

                if st.button(
                    "🔄 開始還原",
                    type="primary",
                    key="restore-do",
                    disabled=not chosen,
                ):
                    with st.spinner("還原中..."):
                        result = backup_lib.restore_backup(
                            zip_bytes,
                            selected=chosen,
                            overwrite=overwrite,
                        )
                    if result["errors"]:
                        for e in result["errors"]:
                            st.error(f"❌ {e}")
                    if result["restored_files"]:
                        st.success(
                            f"✅ 已還原 {result['restored_files']} 個檔案，"
                            f"涵蓋：{', '.join(result['items_restored'])}"
                        )
                    if result["skipped_files"]:
                        st.info(
                            f"⏭️ 跳過 {result['skipped_files']} 個檔案"
                            "（已存在且未勾「覆寫」）"
                        )
                    if not result["restored_files"] and not result["errors"]:
                        st.warning("沒有任何檔案被還原")
