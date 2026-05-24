"""💻 本地模型 — Ollama / LM Studio 偵測與管理"""
from __future__ import annotations

import shutil
import subprocess
import os
from pathlib import Path

import streamlit as st

st.set_page_config(page_title="本地模型 | Claude Code 管家", page_icon="💻", layout="wide")

from lib.ui import inject_style
from lib.nav import render_nav
inject_style(st)
render_nav()

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
        st.info("LM Studio 已安裝但尚未下載任何模型。")

    # 下載新模型
    with st.container(border=True):
        st.markdown("**📥 下載新模型**")
        ld1, ld2 = st.columns([3, 1])
        with ld1:
            lms_new_model = st.text_input(
                "模型名稱",
                placeholder="例如：llama-3.1-8b、qwen2.5-7b-instruct、gemma-2-9b-it",
                key="lms-download",
                label_visibility="collapsed",
            )
        with ld2:
            if st.button("📥 下載", key="lms-dl-btn", type="primary", use_container_width=True, disabled=not lms_new_model.strip()):
                with st.spinner(f"正在透過 LM Studio 下載 {lms_new_model}（可能需要幾分鐘）..."):
                    result = _run(["lms", "get", lms_new_model.strip(), "-y"], timeout=600)
                if result is not None:
                    st.success(f"✅ 已下載 {lms_new_model}")
                    st.rerun()
                else:
                    st.error("下載失敗，請確認模型名稱是否正確，或 LM Studio 是否開啟")

        st.caption("🔗 [LM Studio 官網 →](https://lmstudio.ai)　在 App 搜尋欄也可以找模型")

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

    # ── CC Switch：Claude Code 切換 AI 後端 ──
    st.divider()
    st.subheader("🔀 CC Switch — 一鍵切換 Claude Code 的 AI 後端")
    st.caption("用圖形介面切換 Claude Code 使用的模型：本地模型、DeepSeek、OpenRouter 等")

    with st.expander("❓ CC Switch 是什麼？", expanded=False):
        st.markdown("""
### 一句話解釋

[CC Switch](https://github.com/farion1231/cc-switch) 是一個**獨立的桌面應用程式**，讓你用圖形介面一鍵切換 Claude Code 的 AI 後端。

### 支援的後端

| 後端 | 說明 |
|------|------|
| 🏠 **LM Studio / Ollama** | 本地模型，完全離線免費 |
| 🔷 **DeepSeek** | 高性價比雲端模型 |
| 🌐 **OpenRouter** | 多模型聚合平台 |
| 🟢 **OpenAI** | GPT 系列模型 |
| ☁️ **Anthropic** | 切換回官方 Claude |

### 為什麼要用？

- **不用記指令** — 圖形介面點一下就切換
- **不用改設定檔** — CC Switch 自動幫你寫入 `~/.claude/settings.json`
- **隨時切回來** — 一鍵切換回官方 Claude

### 也有 CLI 版本

不想裝桌面版的話，也有 [cc-switch-cli](https://github.com/saladday/cc-switch-cli)，在終端機操作。
""")

    # 偵測 CC Switch 是否已安裝
    cc_switch_installed = False
    cc_switch_path = ""

    # macOS: 檢查 Applications
    mac_app = Path("/Applications/CC Switch.app")
    mac_app2 = Path.home() / "Applications" / "CC Switch.app"
    if mac_app.exists():
        cc_switch_installed = True
        cc_switch_path = str(mac_app)
    elif mac_app2.exists():
        cc_switch_installed = True
        cc_switch_path = str(mac_app2)

    # CLI 版本
    cc_cli = shutil.which("cc-switch") or shutil.which("cc-switch-cli")
    if cc_cli:
        cc_switch_installed = True
        cc_switch_path = cc_cli

    with st.container(border=True):
        h1, h2 = st.columns([3, 1])
        with h1:
            if cc_switch_installed:
                st.markdown("### 🔀 CC Switch ✅")
                st.caption(f"已安裝：`{cc_switch_path}`")
            else:
                st.markdown("### 🔀 CC Switch ⬜")
                st.caption("尚未安裝")
        with h2:
            if cc_switch_installed:
                st.success("已安裝", icon="✅")
            else:
                st.info("未安裝", icon="⬜")

        # 安裝 / 開啟按鈕
        b1, b2, b3 = st.columns(3)
        with b1:
            if not cc_switch_installed:
                if st.button("📥 自動安裝 CC Switch", key="cc-install", type="primary", use_container_width=True):
                    with st.spinner("正在下載並安裝 CC Switch..."):
                        import platform as pf
                        system = pf.system()
                        arch = pf.machine()
                        if system == "Darwin":
                            if arch == "arm64":
                                dmg_url = "https://github.com/farion1231/cc-switch/releases/latest/download/CC.Switch-aarch64.dmg"
                            else:
                                dmg_url = "https://github.com/farion1231/cc-switch/releases/latest/download/CC.Switch-x64.dmg"
                            dl_path = "/tmp/cc-switch.dmg"
                            result = _run(["curl", "-L", "-o", dl_path, dmg_url], timeout=120)
                            if result is not None:
                                _run(["hdiutil", "attach", dl_path, "-nobrowse", "-quiet"], timeout=30)
                                _run(["cp", "-R", "/Volumes/CC Switch/CC Switch.app", "/Applications/"], timeout=30)
                                _run(["hdiutil", "detach", "/Volumes/CC Switch", "-quiet"], timeout=15)
                                _run(["rm", dl_path], timeout=5)
                                st.success("✅ CC Switch 已安裝到 Applications！")
                                st.rerun()
                            else:
                                st.error("下載失敗，請手動到 GitHub 下載")
                        else:
                            st.info("請到 GitHub 下載對應平台的安裝檔")
            else:
                st.button("✅ 已安裝", key="cc-installed", disabled=True, use_container_width=True)

        with b2:
            if cc_switch_installed:
                if st.button("🚀 開啟 CC Switch", key="cc-open", type="primary", use_container_width=True):
                    if cc_switch_path.endswith(".app"):
                        _run(["open", cc_switch_path])
                        st.success("已開啟 CC Switch")
                    elif cc_cli:
                        _run([cc_cli])
                        st.success("已啟動 CC Switch CLI")

        with b3:
            st.link_button("📖 GitHub", "https://github.com/farion1231/cc-switch", use_container_width=True)

        st.caption("🔗 [CC Switch GitHub](https://github.com/farion1231/cc-switch) ｜ [CLI 版本](https://github.com/saladday/cc-switch-cli) ｜ [使用教學](https://ofox.ai/blog/claude-code-switch-tutorial-2026/)")

    # ── 手動切換（不裝 CC Switch 也能用）──
    with st.container(border=True):
        st.markdown("### ⚙️ 手動切換（不需要 CC Switch）")
        st.caption("如果不想安裝 CC Switch，也可以在這裡直接切換 Claude Code 的後端")

        # 偵測目前狀態
        import json as _json
        claude_settings_path = Path.home() / ".claude" / "settings.json"
        try:
            cs = _json.loads(claude_settings_path.read_text()) if claude_settings_path.is_file() else {}
            current_base = cs.get("env", {}).get("ANTHROPIC_BASE_URL", "")
        except Exception:
            cs = {}
            current_base = ""

        if current_base:
            st.warning(f"⚡ 目前 Claude Code 指向：`{current_base}`")
        else:
            st.info("☁️ 目前 Claude Code 使用官方 Anthropic API")

        # 快速切換按鈕
        switch_options = {
            "☁️ Anthropic（官方）": {"url": "", "key": ""},
            "🎬 LM Studio（本地）": {"url": "http://localhost:1234/v1", "key": "lm-studio"},
            "🦙 Ollama（本地）": {"url": "http://localhost:11434/v1", "key": "ollama"},
            "🔷 DeepSeek": {"url": "https://api.deepseek.com", "key": ""},
            "🟢 OpenAI": {"url": "https://api.openai.com/v1", "key": ""},
            "🌐 OpenRouter": {"url": "https://openrouter.ai/api/v1", "key": ""},
        }

        selected_backend = st.radio(
            "選擇後端",
            list(switch_options.keys()),
            horizontal=True,
            key="manual-switch",
            label_visibility="collapsed",
        )

        backend = switch_options[selected_backend]

        if "本地" not in selected_backend and "官方" not in selected_backend and backend["url"]:
            api_key_input = st.text_input(
                "API Key（該後端的）",
                type="password",
                key="manual-switch-key",
                placeholder="輸入該服務的 API Key...",
            )
        else:
            api_key_input = backend["key"]

        if st.button("🔀 套用切換", key="manual-apply", type="primary"):
            try:
                settings = _json.loads(claude_settings_path.read_text()) if claude_settings_path.is_file() else {}
                settings["env"] = settings.get("env", {})
                if backend["url"]:
                    settings["env"]["ANTHROPIC_BASE_URL"] = backend["url"]
                    settings["env"]["ANTHROPIC_API_KEY"] = api_key_input or backend["key"] or "placeholder"
                else:
                    settings["env"].pop("ANTHROPIC_BASE_URL", None)
                    settings["env"].pop("ANTHROPIC_API_KEY", None)
                claude_settings_path.write_text(_json.dumps(settings, indent=2, ensure_ascii=False))
                if backend["url"]:
                    st.success(f"✅ 已切換到 {selected_backend}！重啟 Claude Code 生效")
                else:
                    st.success("✅ 已切換回官方 Anthropic！重啟 Claude Code 生效")
                st.rerun()
            except Exception as e:
                st.error(f"切換失敗：{e}")

    st.divider()

# ── 推薦模型 ──────────────────────────────────────────────
st.subheader("🌟 推薦模型")
st.caption("適合在本機執行的熱門模型，依記憶體需求排列")

recommended = [
    {"name": "Llama 3.1 8B", "provider": "Meta", "ram": "8 GB", "desc": "通用對話，性能均衡",
     "ollama": "llama3.1", "lms": "llama-3.1-8b", "link": "https://ollama.com/library/llama3.1"},
    {"name": "Qwen 2.5 7B", "provider": "Alibaba", "ram": "8 GB", "desc": "中英文雙語，程式碼能力強",
     "ollama": "qwen2.5", "lms": "qwen2.5-7b-instruct", "link": "https://ollama.com/library/qwen2.5"},
    {"name": "Gemma 2 9B", "provider": "Google", "ram": "8 GB", "desc": "Google 開源，推理能力佳",
     "ollama": "gemma2", "lms": "gemma-2-9b-it", "link": "https://ollama.com/library/gemma2"},
    {"name": "Qwen 2.5 Coder 7B", "provider": "Alibaba", "ram": "8 GB", "desc": "程式碼專用，支援多語言",
     "ollama": "qwen2.5-coder", "lms": "qwen2.5-coder-7b-instruct", "link": "https://ollama.com/library/qwen2.5-coder"},
    {"name": "DeepSeek R1 8B", "provider": "DeepSeek", "ram": "8 GB", "desc": "深度推理，開源",
     "ollama": "deepseek-r1:8b", "lms": "deepseek-r1-distill-qwen-8b", "link": "https://ollama.com/library/deepseek-r1"},
    {"name": "Phi-4 14B", "provider": "Microsoft", "ram": "16 GB", "desc": "微軟小而精模型",
     "ollama": "phi4", "lms": "phi-4", "link": "https://ollama.com/library/phi4"},
    {"name": "Llama 3.1 70B", "provider": "Meta", "ram": "48 GB", "desc": "大型模型，接近 GPT-4 水準",
     "ollama": "llama3.1:70b", "lms": "llama-3.1-70b-instruct", "link": "https://ollama.com/library/llama3.1:70b"},
]

from lib.hardware import detect_hardware
hw = detect_hardware()

has_any_tool = ollama_path or lms_path

for m in recommended:
    ram_needed = int(m["ram"].split()[0])
    can_run = hw.ram_total_gb >= ram_needed

    with st.container(border=True):
        r1, r2, r3, r4, r5 = st.columns([3, 1, 1, 1, 1])
        with r1:
            st.markdown(f"**{m['name']}**")
            st.caption(f"{m['provider']} · {m['desc']}")
        with r2:
            if can_run:
                st.caption(f"💾 需要 {m['ram']}")
            else:
                st.caption(f"⚠️ 需要 {m['ram']}（你有 {hw.ram_total_gb:.0f} GB）")
        with r3:
            st.link_button("📖 詳情", m["link"], use_container_width=True)
        with r4:
            if ollama_path:
                if st.button("🦙 Ollama 安裝", key=f"rec-ollama-{m['ollama']}", use_container_width=True, disabled=not can_run):
                    with st.spinner(f"正在透過 Ollama 下載 {m['ollama']}..."):
                        result = _run(["ollama", "pull", m["ollama"]], timeout=600)
                    if result is not None:
                        st.success(f"✅ 已透過 Ollama 下載 {m['name']}")
                        st.rerun()
                    else:
                        st.error("下載失敗，請確認 Ollama 服務是否啟動")
            else:
                st.button("🦙 需要 Ollama", key=f"rec-ollama-dis-{m['ollama']}", disabled=True, use_container_width=True)
        with r5:
            if lms_path:
                if st.button("🎬 LM Studio 安裝", key=f"rec-lms-{m['lms']}", use_container_width=True, disabled=not can_run):
                    with st.spinner(f"正在透過 LM Studio 下載 {m['lms']}..."):
                        result = _run(["lms", "get", m["lms"], "-y"], timeout=600)
                    if result is not None:
                        st.success(f"✅ 已透過 LM Studio 下載 {m['name']}")
                        st.rerun()
                    else:
                        st.error("下載失敗，請確認 LM Studio 是否開啟")
            else:
                st.button("🎬 需要 LM Studio", key=f"rec-lms-dis-{m['lms']}", disabled=True, use_container_width=True)

    if not has_any_tool:
        break

if not has_any_tool:
    st.warning("⚠️ 需要安裝 Ollama 或 LM Studio 才能下載模型。請先在上方安裝其中一個工具。")
