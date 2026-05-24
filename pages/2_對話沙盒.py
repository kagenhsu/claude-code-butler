"""💬 對話沙盒 — 跟 AI 討論想法，再送到 Claude Code 執行"""
from __future__ import annotations

import base64
import json
import os
import time
import urllib.request
import urllib.error
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

import streamlit as st

from lib import secrets_store
from lib.paths import config_file

st.set_page_config(page_title="對話沙盒 | Claude Code 管家", page_icon="💬", layout="wide")

from lib.ui import inject_style
from lib.nav import render_nav
inject_style(st)
render_nav()

st.title("💬 對話沙盒")
st.caption("跟 AI 討論想法、規劃方案，確認好了再送到 Claude 桌面版 / VS Code / Claude Code 執行")

# ── 說明 ──────────────────────────────────────────────────
with st.expander("❓ 對話沙盒怎麼用？", expanded=False):
    st.markdown("""
### 工作流程

```
💬 對話沙盒（討論想法）→ 確認方案 → 🖥️ Claude 桌面版 / 📝 VS Code / 💻 Claude Code
```

### 為什麼不直接在 Claude Code 討論？

- **不會改檔案** — 純聊天，沒有風險
- **可用便宜模型** — Haiku / GPT-4o mini / DeepSeek，省主力模型額度
- **可上傳檔案** — 圖片、程式碼、文件都能丟進來輔助討論

### 討論好之後

每個 AI 回答下方都有按鈕，可以一鍵送到：
- 🖥️ **Claude 桌面版** — 用 Cowork 功能做更詳細的規劃
- 📝 **VS Code** — 在編輯器裡直接讓 Claude Code 擴充套件執行
- 💻 **Claude Code CLI** — 存成任務檔到終端機執行
""")

# ── 載入設定 ──────────────────────────────────────────────
cfg = secrets_store.load_config()
providers_cfg = cfg.get("providers", {})

def _get_key(provider_id: str, env_var: str) -> str:
    # 走加密儲存：encrypted_api_keys → 舊版 api_keys / providers[*].api_key → 環境變數
    key = secrets_store.get_api_key(provider_id, include_env=False)
    if key:
        return key
    return os.environ.get(env_var, "")

# ── 可用模型列表 ──────────────────────────────────────────
AVAILABLE_MODELS: list[dict] = []

if shutil.which("claude"):
    AVAILABLE_MODELS.append({"id": "claude-code", "name": "Claude Code（你的訂閱）", "provider": "claude-code", "emoji": "🧠", "cost": "訂閱制", "vision": True})

anthropic_key = _get_key("anthropic", "ANTHROPIC_API_KEY")
if anthropic_key:
    AVAILABLE_MODELS.extend([
        {"id": "claude-sonnet-4-6", "name": "Claude Sonnet 4.6", "provider": "anthropic", "emoji": "🟣", "cost": "💰💰", "vision": True},
        {"id": "claude-haiku-4-5-20251001", "name": "Claude Haiku 4.5", "provider": "anthropic", "emoji": "🟣", "cost": "💰", "vision": True},
    ])

openai_key = _get_key("openai", "OPENAI_API_KEY")
if openai_key:
    AVAILABLE_MODELS.extend([
        {"id": "gpt-4o", "name": "GPT-4o", "provider": "openai", "emoji": "🟢", "cost": "💰💰", "vision": True},
        {"id": "gpt-4o-mini", "name": "GPT-4o mini", "provider": "openai", "emoji": "🟢", "cost": "💰", "vision": True},
    ])

gemini_key = _get_key("gemini", "GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY", "")
if gemini_key:
    AVAILABLE_MODELS.extend([
        {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "provider": "gemini", "emoji": "🔵", "cost": "💰", "vision": True},
    ])

minimax_key = _get_key("minimax", "MINIMAX_API_KEY")
if minimax_key:
    AVAILABLE_MODELS.append({"id": "MiniMax-Text-01", "name": "MiniMax-Text-01", "provider": "minimax", "emoji": "🟡", "cost": "💰💰", "vision": False})

deepseek_key = _get_key("deepseek", "DEEPSEEK_API_KEY")
if deepseek_key:
    AVAILABLE_MODELS.append({"id": "deepseek-chat", "name": "DeepSeek V3", "provider": "deepseek", "emoji": "🔷", "cost": "💰", "vision": False})

xai_key = _get_key("xai", "XAI_API_KEY")
if xai_key:
    AVAILABLE_MODELS.append({"id": "grok-3-mini", "name": "Grok 3 mini", "provider": "xai", "emoji": "⚫", "cost": "💰", "vision": True})

mistral_key = _get_key("mistral", "MISTRAL_API_KEY")
if mistral_key:
    AVAILABLE_MODELS.append({"id": "mistral-small-latest", "name": "Mistral Small", "provider": "mistral", "emoji": "🟠", "cost": "💰", "vision": False})

if shutil.which("ollama"):
    try:
        r = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            for line in r.stdout.strip().split("\n")[1:]:
                parts = line.split()
                if parts:
                    AVAILABLE_MODELS.append({"id": f"ollama:{parts[0]}", "name": f"{parts[0]}（Ollama）", "provider": "ollama", "emoji": "🦙", "cost": "免費", "vision": False})
    except Exception:
        pass

if shutil.which("lms"):
    try:
        r = subprocess.run(["lms", "ps"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            lines = r.stdout.strip().split("\n")
            if len(lines) > 1:
                for line in lines[1:]:
                    parts = line.strip().split()
                    if parts:
                        AVAILABLE_MODELS.append({"id": f"lmstudio:{parts[0]}", "name": f"{parts[0]}（LM Studio）", "provider": "lmstudio", "emoji": "🎬", "cost": "免費", "vision": False})
        if not any(m["provider"] == "lmstudio" for m in AVAILABLE_MODELS):
            r2 = subprocess.run(["lms", "status"], capture_output=True, text=True, timeout=5)
            if r2.returncode == 0 and "ON" in r2.stdout:
                AVAILABLE_MODELS.append({"id": "lmstudio:default", "name": "LM Studio（本地）", "provider": "lmstudio", "emoji": "🎬", "cost": "免費", "vision": False})
    except Exception:
        pass


# ── API 呼叫函式 ──────────────────────────────────────────
def _call_claude_code(messages: list, system: str) -> str:
    prompt_parts = []
    if system:
        prompt_parts.append(f"[角色指令] {system}\n")
    for m in messages:
        if m["role"] == "user":
            content = m["content"] if isinstance(m["content"], str) else m["content"][0].get("text", "") if m["content"] else ""
            prompt_parts.append(content)
    r = subprocess.run(["claude", "-p", "\n\n".join(prompt_parts)], capture_output=True, text=True, timeout=120)
    return r.stdout.strip() if r.returncode == 0 else f"❌ Claude Code 執行失敗：{r.stderr.strip()[:200]}"

def _build_anthropic_content(messages: list) -> list:
    result = []
    for m in messages:
        if isinstance(m["content"], str):
            result.append({"role": m["role"], "content": m["content"]})
        elif isinstance(m["content"], list):
            result.append({"role": m["role"], "content": m["content"]})
    return result

def _call_anthropic(model: str, messages: list, system: str, max_tokens: int) -> str:
    body: dict = {"model": model, "max_tokens": max_tokens, "messages": _build_anthropic_content(messages)}
    if system:
        body["system"] = system
    req = urllib.request.Request(
        "https://api.anthropic.com/v1/messages",
        data=json.dumps(body).encode(),
        headers={"x-api-key": anthropic_key, "anthropic-version": "2023-06-01", "content-type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    return data["content"][0]["text"]

def _build_openai_content(messages: list, system: str) -> list:
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    for m in messages:
        if isinstance(m["content"], str):
            msgs.append({"role": m["role"], "content": m["content"]})
        elif isinstance(m["content"], list):
            parts = []
            for p in m["content"]:
                if p.get("type") == "text":
                    parts.append({"type": "text", "text": p["text"]})
                elif p.get("type") == "image":
                    parts.append({"type": "image_url", "image_url": {"url": f"data:{p['media_type']};base64,{p['data']}"}})
            msgs.append({"role": m["role"], "content": parts})
    return msgs

def _call_openai_compatible(url: str, key: str, model: str, messages: list, system: str, max_tokens: int) -> str:
    msgs = _build_openai_content(messages, system)
    req = urllib.request.Request(
        url,
        data=json.dumps({"model": model, "messages": msgs, "max_tokens": max_tokens}).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    return data["choices"][0]["message"]["content"]

def _call_gemini(model: str, messages: list, system: str, max_tokens: int) -> str:
    contents = []
    for m in messages:
        role = "user" if m["role"] == "user" else "model"
        if isinstance(m["content"], str):
            contents.append({"role": role, "parts": [{"text": m["content"]}]})
        elif isinstance(m["content"], list):
            parts = []
            for p in m["content"]:
                if p.get("type") == "text":
                    parts.append({"text": p["text"]})
                elif p.get("type") == "image":
                    parts.append({"inline_data": {"mime_type": p["media_type"], "data": p["data"]}})
            contents.append({"role": role, "parts": parts})
    body: dict = {"contents": contents, "generationConfig": {"maxOutputTokens": max_tokens}}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    return data["candidates"][0]["content"]["parts"][0]["text"]

def call_model(model_info: dict, messages: list, system: str, max_tokens: int) -> str:
    provider = model_info["provider"]
    model_id = model_info["id"]
    try:
        if provider == "claude-code":
            return _call_claude_code(messages, system)
        elif provider == "anthropic":
            return _call_anthropic(model_id, messages, system, max_tokens)
        elif provider == "openai":
            return _call_openai_compatible("https://api.openai.com/v1/chat/completions", openai_key, model_id, messages, system, max_tokens)
        elif provider == "gemini":
            return _call_gemini(model_id, messages, system, max_tokens)
        elif provider == "minimax":
            return _call_openai_compatible("https://api.minimax.chat/v1/text/chatcompletion_v2", minimax_key, model_id, messages, system, max_tokens)
        elif provider == "deepseek":
            return _call_openai_compatible("https://api.deepseek.com/chat/completions", deepseek_key, model_id, messages, system, max_tokens)
        elif provider == "xai":
            return _call_openai_compatible("https://api.x.ai/v1/chat/completions", xai_key, model_id, messages, system, max_tokens)
        elif provider == "mistral":
            return _call_openai_compatible("https://api.mistral.ai/v1/chat/completions", mistral_key, model_id, messages, system, max_tokens)
        elif provider == "ollama":
            return _call_openai_compatible("http://localhost:11434/v1/chat/completions", "ollama", model_id.replace("ollama:", ""), messages, system, max_tokens)
        elif provider == "lmstudio":
            return _call_openai_compatible("http://localhost:1234/v1/chat/completions", "lm-studio", model_id.replace("lmstudio:", ""), messages, system, max_tokens)
        else:
            return f"❌ 不支援的模型提供者：{provider}"
    except urllib.error.HTTPError as e:
        body_text = ""
        try:
            body_text = e.read().decode()[:200]
        except Exception:
            pass
        return f"❌ API 錯誤（HTTP {e.code}）：{body_text}"
    except Exception as e:
        return f"❌ 呼叫失敗：{e}"


# ── Session State ──────────────────────────────────────────
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "send_to_cc" not in st.session_state:
    st.session_state.send_to_cc = None
if "uploaded_files_data" not in st.session_state:
    st.session_state.uploaded_files_data = []
if "saved_chats" not in st.session_state:
    # 從檔案載入歷史對話
    _chats_dir = Path.home() / ".claude" / "sandbox_chats"
    _chats_dir.mkdir(parents=True, exist_ok=True)
    saved = {}
    for f in sorted(_chats_dir.glob("*.json"), reverse=True):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            saved[f.stem] = data
        except Exception:
            pass
    st.session_state.saved_chats = saved
if "current_chat_id" not in st.session_state:
    st.session_state.current_chat_id = None

def _save_current_chat(title: str = "") -> str:
    if not st.session_state.chat_messages:
        return ""
    chat_id = st.session_state.current_chat_id or datetime.now().strftime("%Y%m%d_%H%M%S")
    if not title:
        first_msg = next((m.get("display_content") or m.get("content", "") for m in st.session_state.chat_messages if m["role"] == "user"), "")
        title = (first_msg[:30] + "...") if len(first_msg) > 30 else first_msg
    # 只存文字內容，不存 base64 圖片
    clean_msgs = []
    for m in st.session_state.chat_messages:
        clean_msgs.append({
            "role": m["role"],
            "content": m.get("display_content") or (m["content"] if isinstance(m["content"], str) else ""),
            "model": m.get("model", ""),
        })
    data = {"title": title, "messages": clean_msgs, "timestamp": datetime.now().isoformat()}
    chats_dir = Path.home() / ".claude" / "sandbox_chats"
    chats_dir.mkdir(parents=True, exist_ok=True)
    (chats_dir / f"{chat_id}.json").write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    st.session_state.saved_chats[chat_id] = data
    st.session_state.current_chat_id = chat_id
    return chat_id

def _load_chat(chat_id: str) -> None:
    data = st.session_state.saved_chats.get(chat_id, {})
    st.session_state.chat_messages = [
        {"role": m["role"], "content": m["content"], "display_content": m["content"], "model": m.get("model", "")}
        for m in data.get("messages", [])
    ]
    st.session_state.current_chat_id = chat_id
    st.session_state.send_to_cc = None
    st.session_state.uploaded_files_data = []

def _delete_chat(chat_id: str) -> None:
    chats_dir = Path.home() / ".claude" / "sandbox_chats"
    f = chats_dir / f"{chat_id}.json"
    if f.exists():
        f.unlink()
    st.session_state.saved_chats.pop(chat_id, None)
    if st.session_state.current_chat_id == chat_id:
        st.session_state.current_chat_id = None
        st.session_state.chat_messages = []

# ── 頂部工具列 ──────────────────────────────────────────────
if not AVAILABLE_MODELS:
    st.warning("⚠️ 沒有可用的模型。請先到「雲端模型」設定 API Key，或啟動本地模型。")
    st.stop()

model_names = [f"{m['emoji']} {m['name']}（{m['cost']}）" for m in AVAILABLE_MODELS]

role_presets = {
    "無（預設）": "",
    "規劃助手": "你是一個專案規劃助手。幫使用者釐清需求、拆解任務、提出實作方案。回答使用繁體中文，條列式呈現，最後給出一個可以直接交給工程師執行的明確指令。",
    "程式碼顧問": "你是一個資深軟體工程師。幫使用者分析技術方案、評估可行性、指出潛在風險。回答使用繁體中文，給出具體的程式碼建議和檔案結構。",
    "繁體中文助手": "你是一個繁體中文助手，所有回答都使用繁體中文。回答要簡潔、清楚、實用。",
    "自訂...": "__custom__",
}

if "session_usage" not in st.session_state:
    st.session_state.session_usage = {"calls": 0, "total_time": 0.0, "errors": 0}
usage = st.session_state.session_usage
msg_count = len([m for m in st.session_state.chat_messages if m["role"] == "user"])

# 訂閱制流量限制參考
plan_info = ""
anthropic_plan = providers_cfg.get("anthropic", {})
if anthropic_plan.get("mode") == "subscription":
    plan_name = anthropic_plan.get("plan_name", "")
    if "Max 20x" in plan_name:
        plan_info = "Max 20x"
    elif "Max 5x" in plan_name:
        plan_info = "Max 5x"
    elif "Pro" in plan_name:
        plan_info = "Pro"
    else:
        plan_info = "Free"
elif shutil.which("claude"):
    plan_info = "訂閱制"

top1, top2, top3, top4 = st.columns([4, 1, 1, 1])

with top1:
    selected_idx = st.selectbox(
        "模型",
        range(len(AVAILABLE_MODELS)),
        format_func=lambda i: model_names[i],
        label_visibility="collapsed",
    )
    current_model = AVAILABLE_MODELS[selected_idx]

with top2:
    with st.popover("📚 紀錄", use_container_width=True):
        st.markdown("**對話紀錄**")
        if st.session_state.chat_messages:
            if st.button("💾 儲存目前對話", use_container_width=True, type="primary"):
                _save_current_chat()
                st.success("✅ 已儲存")
            st.divider()
        if st.session_state.saved_chats:
            for cid, cdata in list(st.session_state.saved_chats.items())[:10]:
                title = cdata.get("title", cid)
                ts = cdata.get("timestamp", "")[:10]
                c1, c2 = st.columns([3, 1])
                with c1:
                    if st.button(f"💬 {title}", key=f"load-{cid}", use_container_width=True):
                        _load_chat(cid)
                        st.rerun()
                with c2:
                    if st.button("🗑️", key=f"del-chat-{cid}"):
                        _delete_chat(cid)
                        st.rerun()
        else:
            st.caption("還沒有儲存的對話")

with top3:
    if st.button("🗑️ 新對話", use_container_width=True):
        if st.session_state.chat_messages:
            _save_current_chat()
        st.session_state.chat_messages = []
        st.session_state.send_to_cc = None
        st.session_state.uploaded_files_data = []
        st.session_state.current_chat_id = None
        st.session_state.session_usage = {"calls": 0, "total_time": 0.0, "errors": 0}
        st.rerun()

with top4:
    with st.popover("⚙️", use_container_width=True):
        max_tokens = st.slider("回應長度", 256, 4096, 2048, 256)
        st.divider()
        st.markdown("**🔀 比較模式**")
        compare_mode = st.toggle("同時送給多個模型", value=False)
        compare_models = []
        if compare_mode:
            compare_indices = st.multiselect("選擇比較模型", range(len(AVAILABLE_MODELS)), format_func=lambda i: model_names[i], max_selections=3)
            compare_models = [AVAILABLE_MODELS[i] for i in compare_indices]

# 狀態列（一行文字，不用框）
status_parts = [f"💬 {msg_count} 則"]
if usage["calls"]:
    status_parts.append(f"📡 {usage['calls']} 次呼叫")
    status_parts.append(f"⏱️ {usage['total_time']:.1f}s")
if plan_info:
    status_parts.append(f"💳 {plan_info}")
st.caption("　".join(status_parts))

# ── 送出面板 ──────────────────────────────────────────────
if st.session_state.send_to_cc is not None:
    content = st.session_state.send_to_cc
    with st.container(border=True):
        st.markdown("### 🚀 下一步：選擇要送到哪裡")
        st.caption("在對話沙盒討論好的方案，可以送到以下工具繼續執行或深入規劃")

        tab_desktop, tab_vscode, tab_cc, tab_file = st.tabs([
            "🖥️ Claude 桌面版",
            "📝 VS Code",
            "💻 Claude Code CLI",
            "📥 儲存 / 下載",
        ])

        with tab_desktop:
            st.markdown("把對話內容送到 Claude 桌面版，進行更詳細的規劃和討論")

            has_desktop = Path("/Applications/Claude.app").exists() or (Path.home() / "Applications" / "Claude.app").exists()

            if has_desktop:
                d1, d2 = st.columns(2)
                with d1:
                    if st.button("🖥️ 開啟 Claude 桌面版", type="primary", use_container_width=True):
                        subprocess.Popen(["open", "-a", "Claude"])
                        st.success("✅ 已開啟 Claude 桌面版，請手動貼上內容")
                with d2:
                    if st.button("📋 複製內容到剪貼簿", key="copy-desktop", use_container_width=True):
                        subprocess.run(["pbcopy"], input=content.encode(), check=True)
                        st.success("✅ 已複製！切換到 Claude 桌面版貼上即可")

                st.divider()
                st.markdown("**💡 推薦用法**")
                st.markdown("""
1. 點「開啟 Claude 桌面版」+ 「複製內容」
2. 在桌面版貼上，用 Opus 做更詳細的規劃
3. 規劃好後再回到 Claude Code 執行

**桌面版適合：**
- 需要更深入的分析和規劃
- 想跟 Claude 來回討論多輪
- 需要上傳大量參考資料
- 使用 Cowork 功能協作
""")
            else:
                st.warning("⚠️ 未偵測到 Claude 桌面版應用程式")
                st.link_button("📥 下載 Claude 桌面版", "https://claude.ai/download", use_container_width=True)

        with tab_vscode:
            st.markdown("把方案送到 VS Code，使用 Claude Code 擴充套件在編輯器內執行")

            has_vscode = shutil.which("code") is not None

            if has_vscode:
                v1, v2 = st.columns(2)
                with v1:
                    if st.button("📝 開啟 VS Code", type="primary", use_container_width=True):
                        subprocess.Popen(["code", "."])
                        st.success("✅ 已開啟 VS Code")
                with v2:
                    if st.button("💾 存成任務檔案 + 開啟 VS Code", use_container_width=True):
                        task_file = Path.home() / ".claude" / "task.md"
                        task_file.write_text(content, encoding="utf-8")
                        subprocess.Popen(["code", str(task_file)])
                        st.success("✅ 任務檔已存好，VS Code 已開啟")

                st.divider()
                st.markdown("**💡 在 VS Code 使用 Claude Code**")
                st.markdown("""
1. 開啟 VS Code 後，按 `Cmd+Shift+P`（macOS）或 `Ctrl+Shift+P`（Windows）
2. 輸入 `Claude Code` 選擇啟動
3. 貼上討論好的方案，Claude Code 會在編輯器內直接執行
4. 可以即時看到檔案修改、預覽變更

**VS Code 適合：**
- 想一邊看程式碼一邊讓 Claude 修改
- 需要即時預覽變更結果
- 習慣在 IDE 裡工作
""")
            else:
                st.warning("⚠️ 未偵測到 VS Code CLI 指令（`code`）")
                st.link_button("📥 下載 VS Code", "https://code.visualstudio.com", use_container_width=True)

        with tab_cc:
            st.markdown("把方案送到 Claude Code CLI，在終端機裡直接執行任務")
            task_file = Path.home() / ".claude" / "task.md"
            cc1, cc2 = st.columns(2)
            with cc1:
                if st.button("💾 存成任務檔案 → Claude Code 讀取", type="primary", use_container_width=True):
                    task_file.write_text(content, encoding="utf-8")
                    st.success("✅ 已存到 `~/.claude/task.md`")
                    st.info("在 Claude Code 輸入：\n\n`請讀取 ~/.claude/task.md 並執行裡面的任務`")
            with cc2:
                safe = content.replace("'", "'\\''")
                st.code(f"claude -p '{safe[:100]}...'", language="bash")
                st.caption("複製上面的指令貼到終端機執行")

            st.divider()
            st.markdown("**💡 Claude Code CLI 適合：**")
            st.markdown("""
- 在終端機快速執行任務
- 搭配 shell 腳本自動化
- 不需要開啟 IDE
""")

        with tab_file:
            st.markdown("儲存對話內容為檔案，方便之後參考")
            f1, f2 = st.columns(2)
            with f1:
                st.download_button("📥 下載 Markdown", content, file_name=f"討論_{datetime.now().strftime('%Y%m%d_%H%M')}.md", mime="text/markdown", use_container_width=True)
            with f2:
                st.download_button("📥 下載純文字", content, file_name=f"討論_{datetime.now().strftime('%Y%m%d_%H%M')}.txt", mime="text/plain", use_container_width=True)

        st.divider()
        st.markdown("**📄 預覽內容**")
        with st.expander("點開查看要送出的內容", expanded=False):
            st.markdown(content)

        if st.button("✖️ 關閉此面板", key="close-cc", use_container_width=True):
            st.session_state.send_to_cc = None
            st.rerun()
    st.divider()

# ── 對話紀錄顯示 ──────────────────────────────────────────
for i, msg in enumerate(st.session_state.chat_messages):
    with st.chat_message(msg["role"]):
        # 顯示附件圖片
        if msg.get("images"):
            img_cols = st.columns(min(len(msg["images"]), 3))
            for j, img in enumerate(msg["images"]):
                with img_cols[j % 3]:
                    st.image(f"data:{img['media_type']};base64,{img['data']}", width=200)

        # 顯示附件文字檔
        if msg.get("files_text"):
            for ft in msg["files_text"]:
                with st.expander(f"📄 {ft['name']}", expanded=False):
                    st.code(ft["text"][:2000], language=None)

        # 顯示訊息文字
        st.markdown(msg["display_content"] if msg.get("display_content") else msg["content"] if isinstance(msg["content"], str) else "")

        # AI 回應動作按鈕
        if msg["role"] == "assistant":
            b1, b2, b3, b4 = st.columns([1, 1, 1, 1])
            with b1:
                if st.button("🚀 下一步", key=f"next-{i}", type="primary", use_container_width=True):
                    full = ""
                    for m in st.session_state.chat_messages[:i+1]:
                        role = "使用者" if m["role"] == "user" else "AI"
                        text = m.get("display_content") or (m["content"] if isinstance(m["content"], str) else "")
                        full += f"## {role}\n{text}\n\n"
                    st.session_state.send_to_cc = full
                    st.rerun()
            with b2:
                if st.button("🖥️ 桌面版", key=f"desk-{i}", use_container_width=True):
                    text = msg["display_content"] if msg.get("display_content") else (msg["content"] if isinstance(msg["content"], str) else "")
                    try:
                        subprocess.run(["pbcopy"], input=text.encode(), check=True)
                        subprocess.Popen(["open", "-a", "Claude"])
                        st.success("✅ 已複製並開啟 Claude 桌面版")
                    except Exception:
                        st.session_state.send_to_cc = text
                        st.rerun()
            with b3:
                if st.button("📝 VS Code", key=f"vsc-{i}", use_container_width=True):
                    text = msg["display_content"] if msg.get("display_content") else (msg["content"] if isinstance(msg["content"], str) else "")
                    task_file = Path.home() / ".claude" / "task.md"
                    task_file.write_text(text, encoding="utf-8")
                    subprocess.Popen(["code", str(task_file)])
                    st.success("✅ 已存成任務檔並開啟 VS Code")
            with b4:
                if st.button("📋 複製", key=f"cp-{i}", use_container_width=True):
                    text = msg["display_content"] if msg.get("display_content") else (msg["content"] if isinstance(msg["content"], str) else "")
                    try:
                        subprocess.run(["pbcopy"], input=text.encode(), check=True)
                        st.success("✅ 已複製")
                    except Exception:
                        st.info("請手動複製上方內容")

# ── 輸入區上方：角色 + 附件（摺疊式） ──────────────────────
with st.expander("🎭 角色 ／ 📎 附件", expanded=bool(st.session_state.uploaded_files_data)):
    inp1, inp2 = st.columns(2)
    with inp1:
        selected_role = st.selectbox("🎭 角色指令", list(role_presets.keys()), key="role-preset")
        if role_presets[selected_role] == "__custom__":
            system_prompt = st.text_input("自訂指令", key="custom-sys", placeholder="你是一個...")
        else:
            system_prompt = role_presets[selected_role]
    with inp2:
        uploaded = st.file_uploader(
            "📎 上傳檔案",
            type=["png", "jpg", "jpeg", "gif", "webp", "txt", "md", "py", "js", "ts", "json", "csv", "html", "css"],
            accept_multiple_files=True,
            key="file-upload",
        )
        if uploaded:
            st.session_state.uploaded_files_data = []
            for f in uploaded:
                file_data = {"name": f.name, "type": f.type, "size": f.size}
                if f.type and f.type.startswith("image/"):
                    file_data["kind"] = "image"
                    file_data["base64"] = base64.b64encode(f.read()).decode()
                    file_data["media_type"] = f.type
                else:
                    file_data["kind"] = "text"
                    try:
                        file_data["text"] = f.read().decode("utf-8")
                    except Exception:
                        file_data["text"] = f"（無法讀取 {f.name} 的內容）"
                st.session_state.uploaded_files_data.append(file_data)

    # 顯示已附加的檔案
    if st.session_state.uploaded_files_data:
        file_names = " · ".join(f"{'🖼️' if fd['kind'] == 'image' else '📄'} {fd['name']}" for fd in st.session_state.uploaded_files_data)
        st.caption(f"已附加：{file_names}")

# ── 輸入區 ──────────────────────────────────────────────
prompt = st.chat_input(f"跟 {current_model['name']} 討論你的想法...")

if prompt:
    # 組裝使用者訊息（包含附件）
    attached_images = []
    attached_files = []
    content_parts = []

    if st.session_state.uploaded_files_data:
        for fd in st.session_state.uploaded_files_data:
            if fd["kind"] == "image":
                attached_images.append({"media_type": fd["media_type"], "data": fd["base64"]})
                content_parts.append({"type": "image", "media_type": fd["media_type"], "data": fd["base64"]})
            else:
                attached_files.append({"name": fd["name"], "text": fd["text"]})
                prompt += f"\n\n--- 附件：{fd['name']} ---\n{fd['text']}"

    if content_parts:
        content_parts.insert(0, {"type": "text", "text": prompt})
        msg_content = content_parts
    else:
        msg_content = prompt

    user_msg = {
        "role": "user",
        "content": msg_content,
        "display_content": prompt,
        "images": attached_images,
        "files_text": attached_files,
    }
    st.session_state.chat_messages.append(user_msg)

    with st.chat_message("user"):
        if attached_images:
            img_cols = st.columns(min(len(attached_images), 3))
            for j, img in enumerate(attached_images):
                with img_cols[j % 3]:
                    st.image(f"data:{img['media_type']};base64,{img['data']}", width=200)
        if attached_files:
            for ft in attached_files:
                st.caption(f"📄 {ft['name']}")
        st.markdown(prompt)

    # 清除附件（已加入訊息）
    st.session_state.uploaded_files_data = []

    # 建構 API 訊息
    messages = []
    for m in st.session_state.chat_messages:
        messages.append({"role": m["role"], "content": m["content"]})

    if compare_mode and compare_models:
        cols = st.columns(len(compare_models))
        best_result = ""
        for ci, cmodel in enumerate(compare_models):
            with cols[ci]:
                with st.container(border=True):
                    with st.spinner(f"{cmodel['emoji']} {cmodel['name']}..."):
                        t0 = time.time()
                        result = call_model(cmodel, messages, system_prompt, max_tokens)
                        elapsed = time.time() - t0
                    st.caption(f"{cmodel['emoji']} **{cmodel['name']}**　⏱️ {elapsed:.1f}s")
                    st.markdown(result)
                    st.session_state.session_usage["calls"] += 1
                    st.session_state.session_usage["total_time"] += elapsed
                    if result.startswith("❌"):
                        st.session_state.session_usage["errors"] += 1
                    if ci == 0:
                        best_result = result
        st.session_state.chat_messages.append({"role": "assistant", "content": best_result, "display_content": best_result, "model": "比較模式"})
    else:
        with st.chat_message("assistant"):
            with st.spinner(f"{current_model['emoji']} {current_model['name']} 思考中..."):
                t0 = time.time()
                result = call_model(current_model, messages, system_prompt, max_tokens)
                elapsed = time.time() - t0
            st.markdown(result)
            st.caption(f"{current_model['emoji']} {current_model['name']}　⏱️ {elapsed:.1f}s")
            st.session_state.session_usage["calls"] += 1
            st.session_state.session_usage["total_time"] += elapsed
            if result.startswith("❌"):
                st.session_state.session_usage["errors"] += 1
            if "429" in result:
                st.warning("⚠️ 已達速率限制，請稍等幾分鐘再試")
        st.session_state.chat_messages.append({"role": "assistant", "content": result, "display_content": result, "model": current_model["name"]})

    st.rerun()
