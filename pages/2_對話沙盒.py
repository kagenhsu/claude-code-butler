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

from lib.paths import config_file

st.set_page_config(page_title="對話沙盒 | Claude Code 管家", page_icon="💬", layout="wide")

_css = (Path(__file__).parent.parent / "assets" / "style.css").read_text()
st.markdown(f"<style>{_css}</style>", unsafe_allow_html=True)

# ── 載入設定 ──────────────────────────────────────────────
def _load_config() -> dict:
    cf = config_file()
    if cf.is_file():
        try:
            return json.loads(cf.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}

cfg = _load_config()
api_keys = cfg.get("api_keys", {})
providers_cfg = cfg.get("providers", {})

def _get_key(provider_id: str, env_var: str) -> str:
    p = providers_cfg.get(provider_id, {})
    return p.get("api_key", "") or api_keys.get(provider_id, "") or os.environ.get(env_var, "")

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

# ── 頂部工具列 ──────────────────────────────────────────────
if not AVAILABLE_MODELS:
    st.warning("⚠️ 沒有可用的模型。請先到「雲端模型」設定 API Key，或啟動本地模型。")
    st.stop()

model_names = [f"{m['emoji']} {m['name']}（{m['cost']}）" for m in AVAILABLE_MODELS]

top1, top2, top3, top4, top5 = st.columns([3, 1, 1, 1, 1])

with top1:
    selected_idx = st.selectbox(
        "模型",
        range(len(AVAILABLE_MODELS)),
        format_func=lambda i: model_names[i],
        label_visibility="collapsed",
    )
    current_model = AVAILABLE_MODELS[selected_idx]

with top2:
    with st.popover("⚙️ 設定", use_container_width=True):
        st.markdown("**🎭 角色指令**")
        role_presets = {
            "無（預設）": "",
            "規劃助手": "你是一個專案規劃助手。幫使用者釐清需求、拆解任務、提出實作方案。回答使用繁體中文，條列式呈現，最後給出一個可以直接交給工程師執行的明確指令。",
            "程式碼顧問": "你是一個資深軟體工程師。幫使用者分析技術方案、評估可行性、指出潛在風險。回答使用繁體中文，給出具體的程式碼建議和檔案結構。",
            "繁體中文助手": "你是一個繁體中文助手，所有回答都使用繁體中文。回答要簡潔、清楚、實用。",
            "自訂...": "__custom__",
        }
        selected_role = st.selectbox("角色", list(role_presets.keys()), key="role-preset", label_visibility="collapsed")
        if role_presets[selected_role] == "__custom__":
            system_prompt = st.text_area("自訂指令", height=80, key="custom-sys", placeholder="你是一個...")
        else:
            system_prompt = role_presets[selected_role]

        st.divider()
        max_tokens = st.slider("回應長度", 256, 4096, 2048, 256)

        st.divider()
        st.markdown("**🔀 比較模式**")
        compare_mode = st.toggle("同時送給多個模型", value=False)
        compare_models = []
        if compare_mode:
            compare_indices = st.multiselect("選擇比較模型", range(len(AVAILABLE_MODELS)), format_func=lambda i: model_names[i], max_selections=3)
            compare_models = [AVAILABLE_MODELS[i] for i in compare_indices]

with top3:
    with st.popover("📎 附件", use_container_width=True):
        st.markdown("**上傳檔案加入對話**")
        uploaded = st.file_uploader(
            "選擇檔案",
            type=["png", "jpg", "jpeg", "gif", "webp", "pdf", "txt", "md", "py", "js", "ts", "json", "csv", "html", "css"],
            accept_multiple_files=True,
            key="file-upload",
            label_visibility="collapsed",
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
            st.success(f"已載入 {len(uploaded)} 個檔案")

        if st.session_state.uploaded_files_data:
            st.caption(f"📎 已附加 {len(st.session_state.uploaded_files_data)} 個檔案")
            for fd in st.session_state.uploaded_files_data:
                icon = "🖼️" if fd["kind"] == "image" else "📄"
                st.caption(f"{icon} {fd['name']}")
            if st.button("🗑️ 清除附件"):
                st.session_state.uploaded_files_data = []
                st.rerun()

with top4:
    if st.button("🗑️ 新對話", use_container_width=True):
        st.session_state.chat_messages = []
        st.session_state.send_to_cc = None
        st.session_state.uploaded_files_data = []
        st.rerun()

with top5:
    with st.popover("❓", use_container_width=True):
        st.markdown("""
**對話沙盒**

跟 AI 討論想法，確認好方案後按「🚀 送到 Claude Code」去執行。

**工作流程**
```
討論想法 → 確認方案 → 送到 Claude Code
```

**為什麼不直接在 Claude Code 討論？**
- 對話沙盒不會改檔案，純聊天無風險
- 可用便宜模型討論，省下主力模型額度
- 可上傳圖片/檔案輔助討論
""")

# ── 使用量狀態列 ──────────────────────────────────────────
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
        plan_info = "Max 20x — 20 倍速率上限"
    elif "Max 5x" in plan_name:
        plan_info = "Max 5x — 5 倍速率上限"
    elif "Pro" in plan_name:
        plan_info = "Pro — 5 倍速率上限"
    else:
        plan_info = "Free — 基礎速率上限"
elif shutil.which("claude"):
    plan_info = "訂閱制（依方案有速率限制）"

with st.container(border=True):
    u1, u2, u3, u4 = st.columns(4)
    with u1:
        st.caption(f"💬 對話：**{msg_count}** 則")
    with u2:
        st.caption(f"📡 API 呼叫：**{usage['calls']}** 次")
    with u3:
        st.caption(f"⏱️ 總耗時：**{usage['total_time']:.1f}s**")
    with u4:
        if plan_info:
            st.caption(f"💳 {plan_info}")
        elif usage["errors"] > 0:
            st.caption(f"⚠️ 錯誤：**{usage['errors']}** 次")
        else:
            st.caption(f"🤖 {current_model['name']}")

# ── 附件預覽 ──────────────────────────────────────────────
if st.session_state.uploaded_files_data:
    with st.container(border=True):
        file_cols = st.columns(min(len(st.session_state.uploaded_files_data), 4))
        for idx, fd in enumerate(st.session_state.uploaded_files_data):
            with file_cols[idx % 4]:
                if fd["kind"] == "image":
                    st.image(f"data:{fd['media_type']};base64,{fd['base64']}", caption=fd["name"], width=120)
                else:
                    st.caption(f"📄 **{fd['name']}**")
                    st.caption(f"{len(fd['text'])} 字元")

# ── 送到 Claude Code ──────────────────────────────────────
if st.session_state.send_to_cc is not None:
    content = st.session_state.send_to_cc
    with st.container(border=True):
        st.markdown("### 🚀 送到 Claude Code 執行")

        st.code(content, language="markdown")

        task_file = Path.home() / ".claude" / "task.md"
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("💾 存成任務檔案", type="primary", use_container_width=True):
                task_file.write_text(content, encoding="utf-8")
                st.success(f"✅ 已存到 `{task_file}`\n\n在 Claude Code 輸入：\n`請讀取 ~/.claude/task.md 並執行`")
        with col2:
            st.download_button("📥 下載 .md", content, file_name="task.md", mime="text/markdown", use_container_width=True)
        with col3:
            if st.button("關閉", key="close-cc", use_container_width=True):
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
            b1, b2, _, _ = st.columns([1, 1, 1, 3])
            with b1:
                if st.button("🚀 送到 Claude Code", key=f"cc-{i}", use_container_width=True):
                    text = msg["display_content"] if msg.get("display_content") else (msg["content"] if isinstance(msg["content"], str) else "")
                    st.session_state.send_to_cc = text
                    st.rerun()
            with b2:
                if st.button("📋 複製全部對話", key=f"cp-{i}", use_container_width=True):
                    full = ""
                    for m in st.session_state.chat_messages[:i+1]:
                        role = "使用者" if m["role"] == "user" else "AI"
                        text = m.get("display_content") or (m["content"] if isinstance(m["content"], str) else "")
                        full += f"## {role}\n{text}\n\n"
                    st.session_state.send_to_cc = full
                    st.rerun()

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
