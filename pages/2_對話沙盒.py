"""💬 對話沙盒 — 跟 AI 討論想法，再送到 Claude Code 執行"""
from __future__ import annotations

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

st.title("💬 對話沙盒")
st.caption("跟 AI 討論想法、規劃方案，確認好了再送到 Claude Code 執行")

# ── 說明 ──────────────────────────────────────────────────
with st.expander("❓ 對話沙盒是什麼？跟直接用 Claude Code 有什麼不同？", expanded=False):
    st.markdown("""
### 工作流程

```
💬 對話沙盒（討論想法）  →  📋 確認方案  →  🚀 送到 Claude Code（執行）
```

### 為什麼不直接在 Claude Code 裡討論？

| | 對話沙盒 | Claude Code |
|---|---|---|
| **用途** | 討論想法、規劃方案、比較模型 | 執行任務、改檔案、跑指令 |
| **消耗** | 可選便宜/免費模型討論 | 用你訂閱的主力模型執行 |
| **模型** | 可隨時切換不同 AI | 固定用一個模型 |
| **風險** | 純聊天，不會改任何檔案 | 會直接修改程式碼 |

### 推薦用法

1. 在對話沙盒用便宜模型（Haiku / GPT-4o mini / DeepSeek）討論想法
2. 把確認好的方案一鍵複製
3. 貼到 Claude Code 讓主力模型（Opus / Sonnet）去執行
""")

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

# ── 訂閱制模型提示 ──────────────────────────────────────
subscription_providers = []
for pid, pcfg in providers_cfg.items():
    if pcfg.get("mode") == "subscription":
        subscription_providers.append(pcfg.get("plan_name", pid))

# ── 可用模型列表 ──────────────────────────────────────────
AVAILABLE_MODELS: list[dict] = []

# Claude Code 本身（透過訂閱或 CLI）
if shutil.which("claude"):
    AVAILABLE_MODELS.append({
        "id": "claude-code",
        "name": "Claude Code（你的訂閱）",
        "provider": "claude-code",
        "emoji": "🧠",
        "cost": "訂閱制",
    })

anthropic_key = _get_key("anthropic", "ANTHROPIC_API_KEY")
if anthropic_key:
    AVAILABLE_MODELS.extend([
        {"id": "claude-sonnet-4-6", "name": "Claude Sonnet 4.6", "provider": "anthropic", "emoji": "🟣", "cost": "💰💰"},
        {"id": "claude-haiku-4-5-20251001", "name": "Claude Haiku 4.5", "provider": "anthropic", "emoji": "🟣", "cost": "💰"},
    ])

openai_key = _get_key("openai", "OPENAI_API_KEY")
if openai_key:
    AVAILABLE_MODELS.extend([
        {"id": "gpt-4o", "name": "GPT-4o", "provider": "openai", "emoji": "🟢", "cost": "💰💰"},
        {"id": "gpt-4o-mini", "name": "GPT-4o mini", "provider": "openai", "emoji": "🟢", "cost": "💰"},
    ])

gemini_key = _get_key("gemini", "GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY", "")
if gemini_key:
    AVAILABLE_MODELS.extend([
        {"id": "gemini-2.5-flash", "name": "Gemini 2.5 Flash", "provider": "gemini", "emoji": "🔵", "cost": "💰"},
    ])

minimax_key = _get_key("minimax", "MINIMAX_API_KEY")
if minimax_key:
    AVAILABLE_MODELS.extend([
        {"id": "MiniMax-Text-01", "name": "MiniMax-Text-01", "provider": "minimax", "emoji": "🟡", "cost": "💰💰"},
    ])

deepseek_key = _get_key("deepseek", "DEEPSEEK_API_KEY")
if deepseek_key:
    AVAILABLE_MODELS.extend([
        {"id": "deepseek-chat", "name": "DeepSeek V3", "provider": "deepseek", "emoji": "🔷", "cost": "💰"},
    ])

xai_key = _get_key("xai", "XAI_API_KEY")
if xai_key:
    AVAILABLE_MODELS.extend([
        {"id": "grok-3-mini", "name": "Grok 3 mini", "provider": "xai", "emoji": "⚫", "cost": "💰"},
    ])

mistral_key = _get_key("mistral", "MISTRAL_API_KEY")
if mistral_key:
    AVAILABLE_MODELS.extend([
        {"id": "mistral-small-latest", "name": "Mistral Small", "provider": "mistral", "emoji": "🟠", "cost": "💰"},
    ])

if shutil.which("ollama"):
    try:
        r = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=5)
        if r.returncode == 0:
            for line in r.stdout.strip().split("\n")[1:]:
                parts = line.split()
                if parts:
                    AVAILABLE_MODELS.append({"id": f"ollama:{parts[0]}", "name": f"{parts[0]}（Ollama）", "provider": "ollama", "emoji": "🦙", "cost": "免費"})
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
                        AVAILABLE_MODELS.append({"id": f"lmstudio:{parts[0]}", "name": f"{parts[0]}（LM Studio）", "provider": "lmstudio", "emoji": "🎬", "cost": "免費"})
        if not any(m["provider"] == "lmstudio" for m in AVAILABLE_MODELS):
            r2 = subprocess.run(["lms", "status"], capture_output=True, text=True, timeout=5)
            if r2.returncode == 0 and "ON" in r2.stdout:
                AVAILABLE_MODELS.append({"id": "lmstudio:default", "name": "LM Studio（本地）", "provider": "lmstudio", "emoji": "🎬", "cost": "免費"})
    except Exception:
        pass


# ── API 呼叫函式 ──────────────────────────────────────────
def _call_anthropic(model: str, messages: list, system: str, max_tokens: int) -> str:
    body: dict = {"model": model, "max_tokens": max_tokens, "messages": messages}
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

def _call_openai_compatible(url: str, key: str, model: str, messages: list, system: str, max_tokens: int) -> str:
    msgs = []
    if system:
        msgs.append({"role": "system", "content": system})
    msgs.extend(messages)
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
        contents.append({"role": role, "parts": [{"text": m["content"]}]})
    body: dict = {"contents": contents, "generationConfig": {"maxOutputTokens": max_tokens}}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={gemini_key}"
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = json.loads(resp.read())
    return data["candidates"][0]["content"]["parts"][0]["text"]

def _call_claude_code(messages: list, system: str) -> str:
    prompt_parts = []
    if system:
        prompt_parts.append(f"[角色指令] {system}\n")
    for m in messages:
        if m["role"] == "user":
            prompt_parts.append(m["content"])
    full_prompt = "\n\n".join(prompt_parts)
    r = subprocess.run(
        ["claude", "-p", full_prompt],
        capture_output=True, text=True, timeout=120,
    )
    if r.returncode == 0:
        return r.stdout.strip()
    return f"❌ Claude Code 執行失敗：{r.stderr.strip()[:200]}"

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

# ── 側邊欄 ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 💬 對話設定")

    if not AVAILABLE_MODELS:
        st.warning("⚠️ 沒有可用的模型。請先到「雲端模型」設定 API Key，或啟動本地模型。")
        st.stop()

    model_names = [f"{m['emoji']} {m['name']}（{m['cost']}）" for m in AVAILABLE_MODELS]
    selected_idx = st.selectbox(
        "選擇對話模型",
        range(len(AVAILABLE_MODELS)),
        format_func=lambda i: model_names[i],
        help="建議用便宜模型討論想法，確認好再送到 Claude Code 用主力模型執行",
    )
    current_model = AVAILABLE_MODELS[selected_idx]

    st.divider()

    st.markdown("**🎭 角色指令**")
    role_presets = {
        "無（預設）": "",
        "規劃助手": "你是一個專案規劃助手。幫使用者釐清需求、拆解任務、提出實作方案。回答使用繁體中文，條列式呈現，最後給出一個可以直接交給工程師執行的明確指令。",
        "程式碼顧問": "你是一個資深軟體工程師。幫使用者分析技術方案、評估可行性、指出潛在風險。回答使用繁體中文，給出具體的程式碼建議和檔案結構。",
        "繁體中文助手": "你是一個繁體中文助手，所有回答都使用繁體中文。回答要簡潔、清楚、實用。",
        "自訂...": "__custom__",
    }
    selected_role = st.selectbox("快速選擇", list(role_presets.keys()), key="role-preset")
    if role_presets[selected_role] == "__custom__":
        system_prompt = st.text_area("自訂角色指令", height=100, key="custom-system", placeholder="你是一個...")
    else:
        system_prompt = role_presets[selected_role]

    st.divider()

    max_tokens = st.slider("回應長度", 256, 4096, 2048, 256)

    st.divider()

    st.markdown("**🔀 模型比較模式**")
    compare_mode = st.toggle("同時送給多個模型比較", value=False, help="開啟後可選擇最多 3 個模型並排比較回答")

    compare_models = []
    if compare_mode:
        compare_indices = st.multiselect(
            "選擇比較模型",
            range(len(AVAILABLE_MODELS)),
            format_func=lambda i: model_names[i],
            max_selections=3,
        )
        compare_models = [AVAILABLE_MODELS[i] for i in compare_indices]

    st.divider()

    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🗑️ 新對話", use_container_width=True):
            st.session_state.chat_messages = []
            st.session_state.send_to_cc = None
            st.rerun()
    with col_b:
        if st.button("📥 匯出", use_container_width=True, disabled=not st.session_state.chat_messages):
            st.session_state["show_export"] = True

# ── 匯出 ──────────────────────────────────────────────────
if st.session_state.get("show_export") and st.session_state.chat_messages:
    lines = []
    for msg in st.session_state.chat_messages:
        role = "使用者" if msg["role"] == "user" else f"AI（{msg.get('model', '')}）"
        lines.append(f"### {role}\n\n{msg['content']}\n")
    export_md = "\n---\n\n".join(lines)
    with st.container(border=True):
        st.download_button("💾 下載 Markdown", export_md, file_name=f"對話_{datetime.now().strftime('%Y%m%d_%H%M')}.md", mime="text/markdown")
        if st.button("關閉"):
            st.session_state["show_export"] = False
            st.rerun()

# ── 送到 Claude Code ──────────────────────────────────────
if st.session_state.send_to_cc is not None:
    content = st.session_state.send_to_cc
    with st.container(border=True):
        st.markdown("### 🚀 送到 Claude Code 執行")
        st.caption("複製以下內容，貼到 Claude Code 終端機中執行")

        st.code(content, language="markdown")

        # 生成 claude 指令
        safe_content = content.replace("'", "'\\''")
        claude_cmd = f"claude -p '{safe_content}'"

        st.markdown("**或直接執行指令：**")
        st.code(claude_cmd, language="bash")

        # 也可以存成檔案讓 Claude Code 讀取
        task_file = Path.home() / ".claude" / "task.md"
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("💾 存成任務檔案", type="primary", use_container_width=True):
                task_file.write_text(content, encoding="utf-8")
                st.success(f"✅ 已存到 `{task_file}`\n\n在 Claude Code 輸入：\n`請讀取 ~/.claude/task.md 並執行裡面的任務`")
        with col2:
            st.download_button("📥 下載 .md", content, file_name="task.md", mime="text/markdown", use_container_width=True)
        with col3:
            if st.button("關閉", key="close-cc", use_container_width=True):
                st.session_state.send_to_cc = None
                st.rerun()

    st.divider()

# ── 主要對話區 ──────────────────────────────────────────────
if not st.session_state.chat_messages:
    st.info(
        f"💡 目前使用 **{current_model['emoji']} {current_model['name']}** 進行對話。\n\n"
        "跟 AI 討論你的想法，確認方案後按「🚀 送到 Claude Code」讓它去執行。"
    )

for i, msg in enumerate(st.session_state.chat_messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        # AI 回應下方加上動作按鈕
        if msg["role"] == "assistant":
            btn_cols = st.columns([1, 1, 1, 3])
            with btn_cols[0]:
                if st.button("🚀 送到 Claude Code", key=f"cc-{i}", use_container_width=True):
                    st.session_state.send_to_cc = msg["content"]
                    st.rerun()
            with btn_cols[1]:
                if st.button("📋 複製全部對話", key=f"copy-all-{i}", use_container_width=True):
                    full = ""
                    for m in st.session_state.chat_messages[:i+1]:
                        role = "使用者" if m["role"] == "user" else "AI"
                        full += f"## {role}\n{m['content']}\n\n"
                    st.session_state.send_to_cc = full
                    st.rerun()
            with btn_cols[2]:
                if st.button("🔀 用別的模型重答", key=f"retry-{i}", use_container_width=True):
                    st.session_state.chat_messages = st.session_state.chat_messages[:i-1] if i > 0 else []
                    st.session_state["retry_prompt"] = st.session_state.chat_messages[i-1]["content"] if i > 0 and st.session_state.chat_messages else ""
                    st.rerun()

# ── 輸入區 ──────────────────────────────────────────────
prompt = st.chat_input(f"跟 {current_model['name']} 討論你的想法...")

# 處理重試
retry = st.session_state.pop("retry_prompt", None)
if retry:
    prompt = retry

if prompt:
    # 加入使用者訊息
    st.session_state.chat_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 建構訊息歷史
    messages = [{"role": m["role"], "content": m["content"]} for m in st.session_state.chat_messages]

    if compare_mode and compare_models:
        # 比較模式：並排顯示多個模型的回答
        cols = st.columns(len(compare_models))
        best_result = ""
        for ci, cmodel in enumerate(compare_models):
            with cols[ci]:
                with st.container(border=True):
                    with st.spinner(f"{cmodel['emoji']} {cmodel['name']} 思考中..."):
                        t0 = time.time()
                        result = call_model(cmodel, messages, system_prompt, max_tokens)
                        elapsed = time.time() - t0
                    st.caption(f"{cmodel['emoji']} **{cmodel['name']}**　⏱️ {elapsed:.1f}s")
                    st.markdown(result)
                    if ci == 0:
                        best_result = result

        st.session_state.chat_messages.append({
            "role": "assistant",
            "content": best_result,
            "model": f"{compare_models[0]['name']}（比較模式）",
        })
    else:
        # 單模型對話
        with st.chat_message("assistant"):
            with st.spinner(f"{current_model['emoji']} {current_model['name']} 思考中..."):
                t0 = time.time()
                result = call_model(current_model, messages, system_prompt, max_tokens)
                elapsed = time.time() - t0

            st.markdown(result)
            st.caption(f"{current_model['emoji']} {current_model['name']}　⏱️ {elapsed:.1f}s")

        st.session_state.chat_messages.append({
            "role": "assistant",
            "content": result,
            "model": current_model["name"],
        })

    st.rerun()
