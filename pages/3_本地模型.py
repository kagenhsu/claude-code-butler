"""💻 本地模型 — Ollama / LM Studio 偵測與管理"""
from __future__ import annotations

import shutil
import subprocess
import os
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="本地模型 | Claude Code 管家", page_icon="💻", layout="wide")

_css = (Path(__file__).parent.parent / "assets" / "style.css").read_text()
st.markdown(f"<style>{_css}</style>", unsafe_allow_html=True)

st.title("💻 本地模型")
st.caption("管理電腦上的本地大語言模型 — Ollama / LM Studio")


def _run(cmd: list[str], timeout: int = 10) -> str | None:
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return r.stdout.strip() if r.returncode == 0 else None
    except Exception:
        return None


def _format_size(size_bytes: int) -> str:
    if size_bytes >= 1024 ** 3:
        return f"{size_bytes / (1024 ** 3):.1f} GB"
    elif size_bytes >= 1024 ** 2:
        return f"{size_bytes / (1024 ** 2):.0f} MB"
    return f"{size_bytes / 1024:.0f} KB"


# ── 頁面說明 ──────────────────────────────────────────────
with st.expander("❓ 什麼是本地模型？為什麼要用？", expanded=False):
    st.markdown("""
### 什麼是本地模型？

本地模型是在**你自己的電腦**上執行的 AI，不需要連網路，**完全離線、完全隱私**。

### 為什麼要用？

| 優點 | 說明 |
|------|------|
| 🔒 **隱私** | 資料完全不會離開你的電腦 |
| 💰 **免費** | 不需要 API Key，不會產生費用 |
| ⚡ **離線** | 沒有網路也能用 |
| 🔧 **可自訂** | 可以微調、選擇不同量化等級 |

### 需要什麼？

- **記憶體**：至少 8GB RAM（建議 16GB+）
- **硬碟**：每個模型 1~10 GB 不等
- **工具**：安裝 Ollama 或 LM Studio

### Ollama vs LM Studio

| | Ollama | LM Studio |
|---|---|---|
| 介面 | 純指令列 | 圖形化介面 |
| 適合 | 開發者、自動化 | 新手、視覺化操作 |
| 下載模型 | `ollama pull llama3` | 在 App 內搜尋下載 |
| API | OpenAI 相容 | OpenAI 相容 |
""")

# ── 偵測本地工具 ──────────────────────────────────────────
ollama_path = shutil.which("ollama")
lms_path = shutil.which("lms")

st.subheader("🔍 偵測結果")

tool1, tool2 = st.columns(2)

with tool1:
    with st.container(border=True):
        if ollama_path:
            ollama_ver = _run(["ollama", "--version"]) or ""
            st.markdown("### 🦙 Ollama ✅")
            st.caption(f"路徑：`{ollama_path}`")
            if ollama_ver:
                st.caption(f"版本：`{ollama_ver}`")
        else:
            st.markdown("### 🦙 Ollama ❌")
            st.caption("未偵測到")
            st.link_button("前往安裝 Ollama →", "https://ollama.com/download", use_container_width=True)

with tool2:
    with st.container(border=True):
        if lms_path:
            st.markdown("### 🎬 LM Studio ✅")
            st.caption(f"路徑：`{lms_path}`")
            server_status = _run(["lms", "status"])
            if server_status and "ON" in server_status:
                st.success("伺服器：運行中", icon="🟢")
            else:
                st.info("伺服器：未啟動", icon="🔴")
        else:
            st.markdown("### 🎬 LM Studio ❌")
            st.caption("未偵測到 CLI")
            st.link_button("前往下載 LM Studio →", "https://lmstudio.ai", use_container_width=True)

if not ollama_path and not lms_path:
    st.warning("⚠️ 未偵測到任何本地模型工具。請先安裝 Ollama 或 LM Studio。")
    st.stop()

st.divider()

# ── Ollama 模型管理 ──────────────────────────────────────
if ollama_path:
    st.subheader("🦙 Ollama 模型")

    ollama_output = _run(["ollama", "list"])

    if ollama_output:
        lines = ollama_output.strip().split("\n")
        if len(lines) > 1:
            models = []
            for line in lines[1:]:
                parts = line.split()
                if len(parts) >= 4:
                    models.append({
                        "name": parts[0],
                        "id": parts[1] if len(parts) > 1 else "",
                        "size": parts[2] + " " + parts[3] if len(parts) > 3 else parts[2],
                    })

            st.caption(f"共 **{len(models)}** 個模型")

            for m in models:
                with st.container(border=True):
                    c1, c2, c3 = st.columns([3, 1, 1])
                    with c1:
                        st.markdown(f"**`{m['name']}`**")
                    with c2:
                        st.caption(f"大小：{m['size']}")
                    with c3:
                        if st.button("🗑️ 移除", key=f"ollama-del-{m['name']}", use_container_width=True):
                            with st.spinner(f"正在移除 {m['name']}..."):
                                result = _run(["ollama", "rm", m["name"]])
                            if result is not None:
                                st.success(f"已移除 {m['name']}")
                                st.rerun()
                            else:
                                st.error("移除失敗")
        else:
            st.info("Ollama 已安裝但尚未下載任何模型。")
    else:
        st.info("Ollama 已安裝但尚未下載任何模型，或 Ollama 服務未啟動。")

    # 下載新模型
    with st.container(border=True):
        st.markdown("**📥 下載新模型**")
        dl1, dl2 = st.columns([3, 1])
        with dl1:
            new_model = st.text_input(
                "模型名稱",
                placeholder="例如：llama3、qwen2.5、gemma2",
                key="ollama-download",
                label_visibility="collapsed",
            )
        with dl2:
            if st.button("📥 下載", key="ollama-dl-btn", type="primary", use_container_width=True, disabled=not new_model.strip()):
                with st.spinner(f"正在下載 {new_model}（可能需要幾分鐘）..."):
                    result = _run(["ollama", "pull", new_model.strip()], timeout=600)
                if result is not None:
                    st.success(f"✅ 已下載 {new_model}")
                    st.rerun()
                else:
                    st.error(f"下載失敗，請確認模型名稱是否正確")

        st.caption("🔗 [Ollama 模型庫 →](https://ollama.com/library)　瀏覽所有可用模型")

    st.divider()

# ── LM Studio 模型管理 ──────────────────────────────────
if lms_path:
    st.subheader("🎬 LM Studio 模型")

    # 掃描 LM Studio 模型目錄
    lms_models_dir = Path.home() / ".lmstudio" / "models"
    lms_models = []

    if lms_models_dir.is_dir():
        for gguf in sorted(lms_models_dir.rglob("*.gguf")):
            rel = gguf.relative_to(lms_models_dir)
            parts = rel.parts
            size = gguf.stat().st_size

            # 解析資訊
            publisher = parts[0] if len(parts) > 1 else ""
            repo = parts[1] if len(parts) > 2 else ""
            filename = gguf.name

            # 判斷量化等級
            quant = ""
            for q in ["Q8_0", "Q6_K", "Q5_K_M", "Q5_K", "Q4_K_M", "Q4_K", "Q4_0", "Q3_K", "Q2_K", "F16", "FP16", "f16"]:
                if q.lower() in filename.lower():
                    quant = q
                    break

            # 判斷類型
            model_type = "💬 對話" if any(k in filename.lower() for k in ["instruct", "chat", "coder"]) else "📊 嵌入" if any(k in filename.lower() for k in ["embed", "bge", "e5"]) else "🧠 基礎"

            lms_models.append({
                "path": str(gguf),
                "filename": filename,
                "publisher": publisher,
                "repo": repo,
                "size": size,
                "size_display": _format_size(size),
                "quant": quant,
                "type": model_type,
            })

    if lms_models:
        # 總覽
        total_size = sum(m["size"] for m in lms_models)
        st.caption(f"共 **{len(lms_models)}** 個模型，佔用 **{_format_size(total_size)}** 磁碟空間")

        for m in lms_models:
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                with c1:
                    display_name = m["repo"] or m["filename"]
                    st.markdown(f"**{display_name}**")
                    st.caption(f"{m['publisher']} · `{m['filename']}`")
                with c2:
                    st.caption(f"📦 {m['size_display']}")
                with c3:
                    if m["quant"]:
                        st.caption(f"🎚️ {m['quant']}")
                with c4:
                    st.caption(m["type"])
    else:
        st.info("LM Studio 已安裝但尚未下載任何模型。請在 LM Studio App 中搜尋下載。")

    # LM Studio 伺服器控制
    with st.container(border=True):
        st.markdown("**🖥️ LM Studio 伺服器**")
        server_status = _run(["lms", "status"])
        is_running = server_status and "ON" in server_status

        sv1, sv2, sv3 = st.columns([2, 1, 1])
        with sv1:
            if is_running:
                st.success("🟢 伺服器運行中（http://localhost:1234）", icon="🟢")
            else:
                st.info("🔴 伺服器未啟動", icon="🔴")
        with sv2:
            if not is_running:
                if st.button("▶️ 啟動伺服器", key="lms-start", type="primary", use_container_width=True):
                    _run(["lms", "server", "start"])
                    st.success("已啟動")
                    st.rerun()
        with sv3:
            if is_running:
                if st.button("⏹️ 停止伺服器", key="lms-stop", use_container_width=True):
                    _run(["lms", "server", "stop"])
                    st.success("已停止")
                    st.rerun()

        st.caption("🔗 [LM Studio 官網 →](https://lmstudio.ai)　｜　[使用文件 →](https://lmstudio.ai/docs)")

    st.divider()

# ── 推薦模型 ──────────────────────────────────────────────
st.subheader("🌟 推薦模型")
st.caption("適合在本機執行的熱門模型，依記憶體需求排列")

recommended = [
    {"name": "Llama 3.1 8B", "provider": "Meta", "ram": "8 GB", "desc": "通用對話，性能均衡", "ollama": "llama3.1", "link": "https://ollama.com/library/llama3.1"},
    {"name": "Qwen 2.5 7B", "provider": "Alibaba", "ram": "8 GB", "desc": "中英文雙語，程式碼能力強", "ollama": "qwen2.5", "link": "https://ollama.com/library/qwen2.5"},
    {"name": "Gemma 2 9B", "provider": "Google", "ram": "8 GB", "desc": "Google 開源，推理能力佳", "ollama": "gemma2", "link": "https://ollama.com/library/gemma2"},
    {"name": "Qwen 2.5 Coder 7B", "provider": "Alibaba", "ram": "8 GB", "desc": "程式碼專用，支援多語言", "ollama": "qwen2.5-coder", "link": "https://ollama.com/library/qwen2.5-coder"},
    {"name": "DeepSeek R1 8B", "provider": "DeepSeek", "ram": "8 GB", "desc": "深度推理，開源", "ollama": "deepseek-r1:8b", "link": "https://ollama.com/library/deepseek-r1"},
    {"name": "Phi-4 14B", "provider": "Microsoft", "ram": "16 GB", "desc": "微軟小而精模型", "ollama": "phi4", "link": "https://ollama.com/library/phi4"},
    {"name": "Llama 3.1 70B", "provider": "Meta", "ram": "48 GB", "desc": "大型模型，接近 GPT-4 水準", "ollama": "llama3.1:70b", "link": "https://ollama.com/library/llama3.1:70b"},
]

from lib.hardware import detect_hardware
hw = detect_hardware()

for m in recommended:
    ram_needed = int(m["ram"].split()[0])
    can_run = hw.ram_total_gb >= ram_needed

    with st.container(border=True):
        r1, r2, r3, r4 = st.columns([3, 1, 1, 1])
        with r1:
            st.markdown(f"**{m['name']}**")
            st.caption(f"{m['provider']} · {m['desc']}")
        with r2:
            if can_run:
                st.caption(f"💾 需要 {m['ram']}")
            else:
                st.caption(f"⚠️ 需要 {m['ram']}（你只有 {hw.ram_total_gb:.0f} GB）")
        with r3:
            st.link_button("📖 詳情", m["link"], use_container_width=True)
        with r4:
            if ollama_path:
                if st.button("📥 安裝", key=f"rec-{m['ollama']}", use_container_width=True, disabled=not can_run):
                    with st.spinner(f"正在下載 {m['ollama']}..."):
                        result = _run(["ollama", "pull", m["ollama"]], timeout=600)
                    if result is not None:
                        st.success(f"✅ 已下載")
                        st.rerun()
                    else:
                        st.error("下載失敗")
            else:
                st.button("需要 Ollama", key=f"rec-dis-{m['ollama']}", disabled=True, use_container_width=True)
