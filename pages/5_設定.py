"""⚙️ 設定 — 系統資訊、硬體規格、使用量"""
from __future__ import annotations

import platform
import sys
from pathlib import Path

import streamlit as st

from lib.paths import claude_dir, user_skills_dir, config_file
from lib.hardware import detect_hardware, estimate_task_capacity
from lib.usage import detect_usage

st.set_page_config(page_title="設定 | Claude Code 管家", page_icon="⚙️", layout="wide")

_css = (Path(__file__).parent.parent / "assets" / "style.css").read_text()
st.markdown(f"<style>{_css}</style>", unsafe_allow_html=True)

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

# ── 未來功能 ──────────────────────────────────────────────
st.subheader("🔮 規劃中功能（v2）")
st.markdown(
    """
    - 🔑 API Key 管理（Anthropic / OpenAI / Google）— 加密儲存
    - 🎨 主題切換（淺色 / 深色 / 跟系統）
    - 🎯 預設模型切換
    - 📦 備份與還原（Skills、設定、Prompt 庫）
    """
)
